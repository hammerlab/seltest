# -*- coding: utf-8 -*-
"""
seltest means easy browser-based testing with no overhead.
"""
from .seltest import Base, BaseMeta
from .helpers import url, waitfor, waitforjs, dontwaitfor, hide
import seltest

__all__ = ['Base', 'url', 'waitfor', 'waitforjs', 'dontwaitfor']
__author__ = 'Isaac Hodes <isaachodes@gmail.com>'
__version__ = '1.0.1'

