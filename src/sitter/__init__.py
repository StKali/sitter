#!usr/bin/env python
# -*- coding: utf-8 -*-
# date: 2022/11/12

"""
A simple and efficient command-line program framework.
"""

from .setting import PROG, VERSION
from .sitter import Argument, Application, ALL, Command, register, Options, empty

__version__ = VERSION
__name__ = PROG
__author__ = 'St·Kali <clarkmonkey@163.com>'
