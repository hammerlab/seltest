"""
seltest means easy browser-based testing with no overhead.
"""
from seltest import Base, BaseMeta, url, waitfor, CHROME, FIREFOX, CHROME_EXT_PATH, FIREFOX_EXT_PATH
import seltest

__author__ = 'Isaac Hodes <isaachodes@gmail.com>'
__version__ = '0.0.22'

__all__ = ['Base', 'url', 'waitfor']
