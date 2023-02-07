#!usr/bin/env python
# -*- coding: utf-8 -*-
# date: 2022/11/12


from typing import *

import pytest

import sitter
from sitter import Argument, empty
params = pytest.mark.parametrize


class TestPackageSitter:

    def test_version(self):
        version: str = sitter.__version__
        assert isinstance(version, str) and len(version.split('.')) > 2

    def test_name(self) -> NoReturn:
        assert sitter.__name__ == 'sitter'
