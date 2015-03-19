# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import (WebDriverException,
                                        NoSuchElementException)
from selenium.webdriver.common.action_chains import ActionChains

import hashlib
import os
import pkg_resources
import time
import types


CHROME_EXT_PATH = pkg_resources.resource_filename(
    __name__, 'track-requests/chrome.crx')
FIREFOX_EXT_PATH = pkg_resources.resource_filename(
    __name__, 'track-requests/firefoxtrack.xpi')

AJAX_TIMEOUT = 10  # seconds
AJAX_TIMEOUT_MSG = 'Timed out waiting for XMLHTTPRequests to finish.'
GET_PENDING_REQUESTS_JS = 'return window.__SELTEST_PENDING_REQUESTS;'
WAIT_TIMEOUT = 10  # seconds
WAIT_TIMEOUT_MSG = 'Timed out waiting for element {}.'

DEFAULT_WINDOW_SIZE = [2000, 1000]


class BaseMeta(type):
    """Base metaclass that tracks all test functions."""
    def __new__(cls, cls_name, cls_bases, cls_attrs):
        cls_attrs['__test_methods'] = []
        for attr, value in cls_attrs.iteritems():
            if BaseMeta._is_a_test_method(attr, value):
                cls_attrs['__test_methods'].append(value)
                BaseMeta._update_url_with_base_url(value, cls_attrs)
                prefix = cls_name.lower()
                setattr(value, '__name', ('-').join([prefix, attr]))
        cls_attrs['__test_methods'] = BaseMeta._sort_test_methods(
            cls_attrs['__test_methods'])
        return super(
            BaseMeta, cls).__new__(cls, cls_name, cls_bases, cls_attrs)

    @classmethod
    def _update_url_with_base_url(meta, value, cls_attrs):
        if 'base_url' in cls_attrs:
            full_url = cls_attrs['base_url'] + getattr(value, '__url', '')
            setattr(value, '__url', full_url)

    @classmethod
    def _is_a_test_method(meta, attr, value):
        is_method = type(value) == types.FunctionType
        underscored = attr.startswith('_')
        return is_method and not underscored

    @classmethod
    def _sort_test_methods(cls, methods):
        return sorted(methods, key=lambda m: getattr(m, '__name'))


class Base(object):
    """Base from which all tests must inherit from."""
    __metaclass__ = BaseMeta
    window_size = DEFAULT_WINDOW_SIZE

    def __init__(self, driver):
        self.base_url = ''
        self.driver = driver
        self.driver.set_window_size(*self.window_size)
        self.driver.implicitly_wait(10)
        return super(Base, self).__init__()

    def run(self, image_dir):
        passes = True
        tests = type(self).__dict__['__test_methods']
        for test in tests:
            name, url = self._prepare_page(test)
            if not self._screenshot_and_diff(name, image_dir):
                passes = False
        return passes

    def update(self, image_dir):
        tests = type(self).__dict__['__test_methods']
        for test in tests:
            name, url = self._prepare_page(test)
            self._update_screenshot(name, image_dir)

    def _prepare_page(self, test):
        self._reset_mouse_position()
        name, url = self._name_and_url(test)
        self.driver.get(url)
        test(self, self.driver)
        self._handle_waitfors(test)
        time.sleep(0.1)  # Give JS a chance to fire any other AJAX.
        self._wait_for_ajax()
        return name, url

    def _is_element_present(self, sel, text=None):
        # Disable implicit wait at first so we don't double-wait, and reenable
        # at the end.
        self.driver.implicitly_wait(0)
        try:
            el = self.driver.find_element_by_css_selector(sel)
            if text:
                return el.text == text
            else:
                return True
        except NoSuchElementException:
            return False
        finally:
            self.driver.implicitly_wait(WAIT_TIMEOUT)

    def _name_and_url(self, test):
        test_dict = test.__dict__
        name = test_dict['__name']
        url = test_dict['__url']
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
        test_dict = test.__dict__
        waitfor_css_selector = test_dict.get('__waitfor_css_selector')
        waitfor_text = test_dict.get('__waitfor_text')
        if waitfor_css_selector:
            WebDriverWait(self.driver, WAIT_TIMEOUT).until(
                lambda s: self._is_element_present(waitfor_css_selector,
                                                   text=waitfor_text),
                WAIT_TIMEOUT_MSG.format(waitfor_css_selector))

    def _screenshot_and_diff(self, name, image_dir):
        old_path = '{0}/{1}.png'.format(image_dir, name)
        if not os.path.isfile(old_path):
            msg = '  • {0}: no screenshot found, creating for the first time.'
            print msg.format(name)
            self.driver.save_screenshot(old_path)
            return True
        else:
            new_path = '{0}/{1}.NEW.png'.format(image_dir, name)
            self.driver.save_screenshot(new_path)
            if _are_same_files(new_path, old_path):
                os.remove(new_path)
                msg = '  ✓ {0}: no change'
                print msg.format(name)
                return True
            else:
                msg = '  ✗ {0}: screenshots differ, see {1}/{0}.NEW.png'
                print msg.format(name, image_dir)
                return False

    def _update_screenshot(self, name, image_dir):
        path = '{0}/{1}.png'.format(image_dir, name)
        if not os.path.isfile(path):
            msg = '  • {0}: creating for the first time.'
            print msg.format(name)
        else:
            new_path = '{0}/_{1}.png'.format(image_dir, name)
            self.driver.save_screenshot(new_path)
            if _are_same_files(new_path, path):
                msg = '  ✓ {0}: no change'
                print msg.format(name)
            else:
                msg = '  ✗ {0}: screenshots differ, updating'
                print msg.format(name)
            os.remove(new_path)
        self.driver.save_screenshot(path)


def _ajax_is_complete(driver):
    return driver.execute_script(GET_PENDING_REQUESTS_JS) == 0


def _are_same_files(*args):
    hashed = None
    for path in args:
        with open(path) as f:
            next_hashed = hashlib.md5(f.read()).hexdigest()
            if hashed is not None:
                if next_hashed != hashed:
                    return False
            hashed = next_hashed
    return True


def url(url_str=''):
    """
    Decorator for specifying the URL the test shoudl visit, relative to the test
    class's `base_url`.
    """
    def decorator(method):
        method.__url = url_str
        return method
    return decorator


def waitfor(css_selector, text=None):
    """
    Decorator for specifying elements (selected by a CSS-style selector) to
    explicitly wait for before taking a screenshot. If text is set, wait for the
    element to contain that text before taking the screenshot.
    """
    def decorator(method):
        method.__waitfor_css_selector = css_selector
        method.__waitfor_text = text
        return method
    return decorator
