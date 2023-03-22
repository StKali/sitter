#!usr/bin/env python
# -*- coding: utf-8 -*-
# date: 2022/11/12

import pytest
from sitter.util import *


params = pytest.mark.parametrize


def test_empty() -> None:

    assert not empty    
    assert str(empty) == '<empty>'


def test_cached_property():

    class A:
        
        run_count: int = 0

        @cached_property
        def count(self):
            self.run_count += 1
            return self.run_count

    a = A()
    for _ in range(10):
        assert a.count == 1

