# -*- coding: utf-8 -*-
"""
seltest means easy browser-based testing with no overhead.
"""
from .seltest import Base, BaseMeta
from .helpers import url, waitfor, dontwaitfor, hide
import seltest

__all__ = ['Base', 'url', 'waitfor', 'dontwaitfor']
__author__ = 'Isaac Hodes <isaachodes@gmail.com>'
__version__ = '0.2.7'

