#!usr/bin/env python
# -*- coding: utf-8 -*-
# date: 2022/11/12


from typing import *

import pytest

from sitter import Argument, empty, Options
from sitter.sitter import NameMapping
from utils import rand_strings
params = pytest.mark.parametrize


class TestArgument:

    @params('name, argument, result', [
        ('no-params', Argument(), 'short and long all empty'),
        ('invalid-short', Argument(short='n'), 'invalid short argument %r' % 'n'),
        ('invalid-long', Argument(long='-x'), 'invalid long argument %r' % '-x'),
        ('cannot-get-key', Argument(short='-p'), 'key and long cannot be default at the same time'),
    ])
    def test_invalid_argument(self, name, argument, result):
        assert argument.check() == result

    def test_key(self):
        argument = Argument('-x', '--xxx')
        assert argument.key is empty
        assert not argument.check()
        assert argument.key == 'xxx'

        argument = Argument('-x', '--xxx', key='hello')
        assert argument.key == 'hello'

    def test_str(self):
        argument = Argument()
        assert str(argument).startswith('Argument(short')
    
        
def test_name_mapping() -> None:

    name: str = 'test_mapping'
    np: int = NameMapping(name)
    width: int = 0
    assert np.name == name

    for string in rand_strings(10):
        np[string] = string
        width = max((width, len(string)))
    assert np.width == width


def test_options() -> None:

    options = Options()

    options.name = 'monkey'
    assert 'name' in options
