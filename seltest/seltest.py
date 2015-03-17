# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import (WebDriverException,
                                        NoSuchElementException)

import hashlib
import os
import pkg_resources
import time
import types


EXT_PATH = pkg_resources.resource_filename(__name__, 'ext.crx')
AJAX_TIMEOUT = 10  # seconds
AJAX_TIMEOUT_MSG = 'Timed out waiting for XMLHTTPRequests to finish.'
GET_PENDING_REQUESTS_JS = 'return window.__SELTEST_PENDING_REQUESTS;'
WAIT_TIMEOUT = 10  # seconds
WAIT_TIMEOUT_MSG = 'Timed out waiting for element {}.'


class BaseMeta(type):
    """Base metaclass that tracks all test functions."""
    def __new__(cls, cls_name, cls_bases, cls_attrs):
        cls_attrs['__test_methods'] = []
        for attr, value in cls_attrs.iteritems():
            if BaseMeta.__is_a_test_method(attr, value):
                cls_attrs['__test_methods'].append(value)
                prefix = cls_name.lower()
                value.__name = ('-').join([prefix, attr])
        return super(
            BaseMeta, cls).__new__(cls, cls_name, cls_bases, cls_attrs)

    @classmethod
    def __is_a_test_method(cls, attr, value):
        is_method =  type(value) == types.FunctionType
        has_url = hasattr(value, '__url')
        return is_method and has_url


class Base(object):
    """Base from which all tests must inherit from."""
    __metaclass__ = BaseMeta

    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_extension(EXT_PATH)
        self.driver = webdriver.Chrome(chrome_options=options)
        self.driver.set_window_size(2000, 1000)
        self.driver.implicitly_wait(10)
        return super(Base, self).__init__()

    def run(self, image_dir):
        failed = False
        tests = type(self).__dict__['__test_methods']
        for test in tests:
            name, url = self._name_and_url(test)
            self.driver.get(url)
            test(self, self.driver)
            self._handle_waitfors(test)
            time.sleep(0.1)  # Give JS a chance to fire any other AJAX.
            self._wait_for_ajax()
            if not self._screenshot_and_diff(name, image_dir):
                failed = True
        self.driver.quit()
        return not failed

    def _is_element_present(self, sel, text=None):
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
        name = test_dict['_BaseMeta__name']
        url = test_dict['__url']
        return name, url

    def _wait_for_ajax(self):
        self.driver.implicitly_wait(0)
        WebDriverWait(self.driver, AJAX_TIMEOUT).until(
            ajax_is_complete,  AJAX_TIMEOUT_MSG)
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
            new_path = '{0}/NEW_{1}.png'.format(image_dir, name)
            self.driver.save_screenshot(new_path)
            if are_same_files(new_path, old_path):
                os.remove(new_path)
                msg = '  ✓ {0}: no change'
                print msg.format(name)
                return True
            else:
                msg = '  ✗ {0}: screenshots differ, see {1}/NEW_{0}.png'
                print msg.format(name, image_dir)
                return False


def ajax_is_complete(driver):
    return driver.execute_script(GET_PENDING_REQUESTS_JS) == 0


def are_same_files(*args):
    hashed = None
    for path in args:
        with open(path) as f:
            next_hashed = hashlib.md5(f.read()).hexdigest()
            if hashed is not None:
                if next_hashed != hashed:
                    return False
            hashed = next_hashed
    return True


def url(url_str):
    def decorator(method):
        method.__url = url_str
        return method
    return decorator


def waitfor(css_selector, text=None):
    def decorator(method):
        method.__waitfor_css_selector = css_selector
        method.__waitfor_text = text
        return method
    return decorator
