#!usr/bin/env python
# -*- coding: utf-8 -*-
# date: 2022/11/12

"""
A simple and efficient command-line program framework.
"""

from .sitter import (
    Argument, App, ALL, FLEX, SitterError, ParamsParseError, ArgumentError, Command,
    register, Options, empty,
)

__version__ = '0.1.2'
__name__ = 'sitter'
__author__ = 'St·Kali <clarkmonkey@163.com>'
__email__ = 'clarkmonkey@163.com'
