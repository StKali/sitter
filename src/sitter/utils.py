#!usr/bin/env python
# -*- coding: utf-8 -*-
# date: 2022/11/12

"""
A simple utils script
"""

from typing import Any, Optional, Callable, NoReturn

empty: Any = type(
    'EmptyType', (), {
        '__bool__': lambda x: False,
        '__repr__': lambda x: '<empty>',
    })()


class cached_property:
    """ Decorator that converts a method with a single self argument into a
    property cached on the instance.
    """
    name: Optional[str] = None

    @staticmethod
    def func(instance) -> NoReturn:
        raise TypeError(
            'Cannot use cached_property instance without calling '
            '__set_name__() on it.'
        )

    def __init__(self, func: Callable, _: Optional[str] = None) -> None:
        self.real_func: Callable = func
        self.__doc__: str = getattr(func, '__doc__')

    def __set_name__(self, owner: Any, name: str) -> NoReturn:
        if self.name is None:
            self.name: str = name
            self.func: Callable = self.real_func
        elif name != self.name:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                "(%r and %r)." % (self.name, name)
            )

    def __get__(self, instance: Any, cls=None):
        """
        Call the function and put the return value in instance.__dict__ so that
        subsequent attribute access on the instance returns the cached value
        instead of calling cached_property.__get__().
        """
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res
