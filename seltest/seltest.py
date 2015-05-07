# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import PIL.Image as Image
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import (WebDriverException,
                                        NoSuchElementException,
                                        TimeoutException)
from selenium.webdriver.common.action_chains import ActionChains

import hashlib
import os
import pkg_resources
import sys
import time
import types

from seltest.helpers import with_metaclass


AJAX_TIMEOUT = 10  # seconds
AJAX_TIMEOUT_MSG = 'Timed out waiting for XMLHTTPRequests to finish.'
GET_PENDING_REQUESTS_JS = 'return window.__SELTEST_PENDING_REQUESTS;'
WAIT_TIMEOUT = 10  # seconds
WAIT_TIMEOUT_MSG = 'Timed out waiting for: {}.'

DEFAULT_WINDOW_SIZE = [2000, 1800]


class BaseMeta(type):
    """Base metaclass that tracks all test functions."""

    def __new__(cls, cls_name, cls_bases, cls_attrs):
        cls_attrs['__test_methods'] = []
        for attr, value in cls_attrs.items():
            if BaseMeta._is_a_test_method(attr, value):
                cls_attrs['__test_methods'].append(value)
                BaseMeta._update_url_with_base_url(value, cls_attrs)
                BaseMeta._update_waitfors_with_base(value, cls_attrs)
                name = '{}_{}'.format(cls_name.lower(),
                                      '-'.join(attr.split('_')))
                setattr(value, '__name', name)
        cls_attrs['__test_methods'] = BaseMeta._sort_test_methods(
            cls_attrs['__test_methods'])
        return super(
            BaseMeta, cls).__new__(cls, cls_name, cls_bases, cls_attrs)

    @classmethod
    def _update_url_with_base_url(meta, value, cls_attrs):
        module = sys.modules[cls_attrs['__module__']]
        if 'base_url' in cls_attrs:
            full_url = cls_attrs['base_url'] + getattr(value, '__url', '')
            setattr(value, '__url', full_url)
        elif hasattr(module, 'base_url'):
            full_url = module.base_url + getattr(value, '__url', '')
            setattr(value, '__url', full_url)

    @classmethod
    def _update_waitfors_with_base(meta, value, cls_attrs):
        dontwaits = getattr(value, '__dontwait', [])
        if 'wait_for' in cls_attrs:
            waitfor = cls_attrs['wait_for']
            if not waitfor['css_selector'] in dontwaits:
                setattr(value, '__waitfors',
                        [waitfor] + getattr(value, '__waitfors', []))
        elif 'wait_fors' in cls_attrs:
            waitfors = [w for w in cls_attrs['wait_fors']
                        if w['css_selector'] not in dontwaits]
            setattr(value, '__waitfors',
                    waitfors + getattr(value, '__waitfors', []))

    @classmethod
    def _is_a_test_method(meta, attr, value):
        is_method = type(value) == types.FunctionType
        underscored = attr.startswith('_')
        return is_method and not underscored

    @classmethod
    def _sort_test_methods(cls, methods):
        return sorted(methods, key=lambda m: getattr(m, '__name'))


@with_metaclass(BaseMeta)
class Base(object):
    """Base from which all tests must inherit from."""
    def __init__(self, driver):
        __module = sys.modules[self.__module__]
        self.window_size = (getattr(self, 'window_size', None)
                            or getattr(__module, 'window_size', None)
                            or DEFAULT_WINDOW_SIZE)
        self.__test_methods = type(self).__dict__['__test_methods']
        self.base_url = ''
        self.driver = driver
        self.driver.set_window_size(*self.window_size)
        self.driver.implicitly_wait(10)
        return super(Base, self).__init__()

    def hide(self, css_selector):
        """Hide (by setting `hidden=true`) the selected elements."""
        self.driver.execute_script("""
            var els = document.querySelectorAll('{}');
            for (var i = 0; i < els.length; i++) {{
                els[i].hidden = true;
            }};
            """.format(css_selector))

    def _run(self, image_dir, proxy_port, wait=None):
        passes = True
        for test in self.__test_methods:
            name, url = self._name_and_url(test)
            try:
                self._prepare_page(test, name, url, proxy_port)
            except TimeoutException as e:
                print('  ✗ {}: test timed out: {}'.format(name, e))
                passes = False
                continue
            except AssertionError as e:
                print('  ✗ {}: assertion failed: {}'.format(name, e))
                passes = False
                continue
            finally:
                if wait:
                    time.sleep(float(wait))
            if not self._screenshot_and_diff(name, image_dir):
                passes = False
        return passes

    def _update(self, image_dir, proxy_port, wait=None):
        for test in self.__test_methods:
            name, url = self._name_and_url(test)
            try:
                self._prepare_page(test, name, url, proxy_port)
            except TimeoutException as e:
                print('  ✗ {}: test timed out: {}'.format(name, e))
                continue
            except AssertionError as e:
                print('  ✗ {}: assertion failed: {}'.format(name, e))
                continue
            finally:
                if wait:
                    time.sleep(float(wait))
            self._update_screenshot(name, image_dir)

    def _prepare_page(self, test, name, url, proxy_port):
        self._reset_mouse_position()
        self.driver.get('http://localhost:{}/{}'.format(proxy_port, url))
        test(self, self.driver)
        self._handle_waitfors(test)
        time.sleep(0.1)  # Give JS a chance to fire any other AJAX.
        self._wait_for_ajax()
        self._hide_elements(test)

    def _are_waitfors_satisfied(self, test):
        if not getattr(test, '__waitfors', None):
            return True  # If there aren't any waitfors, don't wait.
        results = []
        for waitfor in getattr(test, '__waitfors'):
            sel = waitfor['css_selector']  # required
            text = waitfor.get('text')  # optional
            classes = waitfor.get('classes')  #optional
            try:
                el = self.driver.find_element_by_css_selector(sel)
                text_present = True
                if text:
                    text_present = el.text == text
                has_classes = True
                if classes:
                    el_classes = el.get_attribute('class').split(' ')
                    has_classes = all(c in el_classes for c in classes)
                results.append(text_present and has_classes)
            except NoSuchElementException:
                return False
        return all(results)

    def _name_and_url(self, test):
        name = getattr(test, '__name')
        url = getattr(test, '__url')
        return name, url

    def _reset_mouse_position(self, offset=-10000000):
        action = ActionChains(self.driver)
        action.move_by_offset(offset, offset)
        action.perform()

    def _wait_for_ajax(self):
        self.driver.implicitly_wait(0)
        WebDriverWait(self.driver, AJAX_TIMEOUT).until(
            _ajax_is_complete,  AJAX_TIMEOUT_MSG)
        self.driver.implicitly_wait(WAIT_TIMEOUT)

    def _handle_waitfors(self, test):
        self.driver.implicitly_wait(0)
        WebDriverWait(self.driver, WAIT_TIMEOUT).until(
            lambda s: self._are_waitfors_satisfied(test),
            WAIT_TIMEOUT_MSG.format(self._waitfor_str(test)))
        self.driver.implicitly_wait(WAIT_TIMEOUT)

    def _hide_elements(self, test):
        hidden_selectors = getattr(test, '__hide', [])
        for sel in hidden_selectors:
            self.hide(sel)

    def _waitfor_str(self, test):
        if not getattr(test, '__waitfors', None):
            return ''
        waitstrs = []
        for waitfor in getattr(test, '__waitfors'):
            waitstr = ''
            waitstr += waitfor['css_selector']
            text = waitfor.get('text')
            if text:
                waitstr += ' (text={})'.format(text)
            classes = waitfor.get('classes')
            if classes:
                waitstr += ' (classes={})'.format(' '.join(classes))
            waitstrs.append(waitstr)
        return ', '.join(waitstrs)

    def _screenshot_and_diff(self, name, image_dir):
        old_path = '{0}/{1}.png'.format(image_dir, name)
        if not os.path.isfile(old_path):
            msg = '  • {0}: no screenshot found, creating for the first time.'
            print(msg.format(name))
            self.driver.save_screenshot(old_path)
            return True
        else:
            new_path = '{0}/{1}.NEW.png'.format(image_dir, name)
            self.driver.save_screenshot(new_path)
            if _are_same_files(new_path, old_path):
                os.remove(new_path)
                msg = '  ✓ {0}: no change'
                print(msg.format(name))
                return True
            else:
                msg = '  ✗ {0}: screenshots differ, see {1}/{0}.NEW.png'
                print(msg.format(name, image_dir))
                return False

    def _update_screenshot(self, name, image_dir):
        path = '{0}/{1}.png'.format(image_dir, name)
        if not os.path.isfile(path):
            msg = '  • {0}: creating for the first time.'
            print(msg.format(name))
        else:
            new_path = '{0}/_{1}.png'.format(image_dir, name)
            self.driver.save_screenshot(new_path)
            if _are_same_files(new_path, path):
                msg = '  ✓ {0}: no change'
                print(msg.format(name))
            else:
                msg = '  ✗ {0}: screenshots differ, updating'
                print(msg.format(name))
            os.remove(new_path)
        self.driver.save_screenshot(path)


def _ajax_is_complete(driver):
    return driver.execute_script(GET_PENDING_REQUESTS_JS) == 0


def _are_same_files(*args):
    hashed = None
    for path in args:
        with Image.open(path) as i:
            next_hashed = hashlib.sha512(i.tostring()).hexdigest()
            if hashed is not None:
                if next_hashed != hashed:
                    return False
            hashed = next_hashed
    return True
