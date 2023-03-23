#!usr/bin/env python
# -*- coding: utf-8 -*-
# date: 2022/11/12

"""

"""

import re
import sys
from os import path as op
from functools import lru_cache
from typing import NoReturn, Any, List, Dict, Optional, Callable, Set, Type, Tuple, Iterable, Union

from .util import empty, cached_property

if sys.version_info > (3, 10):
    from types import NoneType
else:
    NoneType: Type = type(None)

SHORT_RGX = re.compile('^-[a-zA-Z0-9]$')
LONG_RGX = re.compile('^--[a-zA-Z][a-zA-Z0-9-]')
FLEX: Any = object()
ALL: Any = object()
CmdType: Type = Type['Command']


class SitterError(Exception):
    """ base sitter error """


class ParamsParseError(SitterError):
    """"""


class ArgumentError(SitterError):
    """"""


if sys.version_info > (3, 8):
    from dataclasses import dataclass

    @dataclass
    class _Argument:
        short: str = ''
        long: str = ''
        default: Any = empty
        docs: str = ''
        count: int = 1
        required: bool = False
        key: str = empty
        mutex: Any = None
        exclusive: bool = False
else:
    class _Argument:

        def __init__(
            self,
            short: str = '',
            long: str = '',
            default: Any = empty,
            docs: str = '',
            count: int = 1,
            required: bool = False,
            key: str = empty,
            mutex: Any = None,
            exclusive: bool = False
        ) -> None:
            self.short: str = short
            self.long: str = long
            self.default: Any = default
            self.docs: str = docs
            self.count: int = count
            self.required: bool = required
            self.key: str = key
            self.mutex: Any = mutex
            self.exclusive: bool = exclusive

        def __repr__(self) -> str:
            return 'Argument(%s)' % ', '.join('%s=%r' % k for k in vars(self).items())


class Argument(_Argument):

    def check(self) -> Optional[str]:

        if not self.short and not self.long:
            return'short and long all empty'

        if self.short and not SHORT_RGX.findall(self.short):
            return f'invalid short argument {self.short!r}'

        if self.long and not LONG_RGX.findall(self.long):
            return f'invalid long argument {self.long!r}'

        if not self.key and not self.long:
            return 'key and long cannot be default at the same time'

        if not self.key:
            self.key = self.long.lstrip('-')

        self.docs = self.docs or 'no help doc'
        if self.count == 0 and self.default is empty:
            self.default = False


def check_error(ret: Any) -> None:
    if not ret:
        return
    print(f'Error: {ret}', file=sys.stderr)
    sys.exit(1)


class NameMapping(dict):

    def __init__(self, name: str, *args, **kwargs) -> None:
        super(NameMapping, self).__init__(*args, **kwargs)
        self.__width: int = 0
        self.name: str = name

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self:
            raise ValueError(key)
        super(NameMapping, self).__setitem__(key, value)
        self.__width: int = max((self.__width, len(key)))

    @property
    def width(self) -> int:
        return self.__width


class CommandMapping(NameMapping):

    def __init__(self,  *args, **kwargs) -> None:
        super(CommandMapping, self).__init__(*args, **kwargs)
        self.__alias_commands: Dict[str, CmdType] = {}

    def add_command(self, command: CmdType) -> None:
        if not isinstance(command.name, str):
            raise TypeError(
                f'Command.name want str object but get {command.name!r}'
            )
        self[command.name] = command
        if command.alias:
            for alias in command.alias:
                if not isinstance(alias, str):
                    raise TypeError(
                        f'alias want str object but get {alias!r}'
                    )
                self.__alias_commands[alias] = command
    
    def match_command(self, name: str) -> Optional[CmdType]:
        return self.get(name, self.__alias_commands.get(name))
    
    def __getitem__(self, key: str) -> CmdType:
        return super().__getitem__(key)
    
    def help(self) -> Iterable[str]:
        yield self.name
        yield '  {%s}' % ','.join(self.keys())
        fmt: str = '    %-{length}s  %s'.format(length=self.width)
        for k, v in self.items():
            yield fmt % (k, v)

    def __contains__(self, key: object) -> bool:
        return super(CommandMapping, self).__contains__(key) or key in self.__alias_commands


class Options(dict):

    def __getitem__(self, key: str) -> Any:

        if key in self:
            return super(Options, self).__getitem__(key)
        raise ParamsParseError(
            f'not matches any value for {key!r} in command line arguments'
        )
    
    def __setitem__(self, key: str, value: Any) -> NoReturn:
        return super(Options, self).__setitem__(key, value)
    
    __getattr__ = __getitem__
    __setattr__ = __setitem__

    def __repr__(self) -> str:
        return 'Options(%s)' % ','.join('%s=%r' % t for t in self.items())
    

class ArgumentMapping(NameMapping):

    def __init__(self, name: str, *args, **kwargs) -> None:
        super(ArgumentMapping, self).__init__(name, *args, **kwargs)
        self.arguments: List[Argument] = list()

    def add_argument(self, arg: Argument) -> None:
        if arg.short:
            self[arg.short] = arg
        if arg.long:
            self[arg.long] = arg
        self.arguments.append(arg)

    def __iter__(self) -> Iterable[Argument]:
        for arg in self.arguments:
            yield arg

    def __repr__(self) -> str:
        return '<%s %s>' % (self.name, super(ArgumentMapping, self).__repr__())

    def help(self) -> str:
        yield self.name
        fmt: str = '    %-4s%-{length}s  %s'.format(length=self.width)
        for arg in self:
            yield fmt % (arg.short, arg.long, arg.docs)


class Parser:

    option_name: str = 'Optional Arguments'
    global_name: str = 'Global Arguments'
    alias_name: str = 'Aliases'
    sample_name: str = 'Samples'

    def __init__(self) -> None:

        self.optionals: ArgumentMapping = ArgumentMapping(self.option_name)
        self.globals: ArgumentMapping = ArgumentMapping(self.global_name)
        self.__keys: Set = set()
        self.__options: Options = Options()

    def has_key(self, key: str) -> bool:
        return key in self.__keys
    
    def set_key(self, key: str) -> bool:
        if key in self.__keys:
            return False
        self.__keys.add(key)
        return True

    def _add_args(self, mapping: ArgumentMapping, arguments: Tuple[Argument]) -> NoReturn:

        for arg in arguments:
            check_error(arg.check())
            if arg in self or not self.set_key(arg.key):
                raise ArgumentError(f'duplicated argument {arg!r}%s')
            mapping.add_argument(arg)

    def add_args(self, *arguments: Argument) -> None:
        self._add_args(self.optionals, arguments)

    def add_global_args(self, *arguments: Argument) -> None:
        self._add_args(self.globals, arguments)

    def clean_argv(self, argv: List[str]) -> Iterable[str]:

        for arg in argv:
            if not arg:
                continue

            if arg[0] != '-':
                yield arg
                continue

            r = arg.split('=', 1)
            if len(r) == 2 and r[0] in self:
                yield r[0]
                yield r[1]
                continue
            yield arg

    def add_option(self, argument: Argument, value: Any) -> NoReturn:
        if argument.key in self.__options:
            data = self.__options[argument.key]
            if isinstance(data, list):
                if isinstance(value, list):
                    data.extend(value)
                else:
                    data.append(value)
            else:
                if isinstance(value, list):
                    data = [data, *value]
                else:
                    data = [data, value]
        else:
            data = value
        self.__options[argument.key] = data
    
    def parse_argv(self, argv: List[str]) -> Tuple[Options, List[str]]:
        mmp: Dict[str, str] = {}
        argv = list(self.clean_argv(argv))
        remains: List[str] = list()
        index, length = 0, len(argv)
        while index < length:
            arg = argv[index]
            index += 1
            if arg not in self:
                remains.append(arg)
                continue

            argument: Argument = self[arg]
            if argument.exclusive and (remains or self.__options):
                raise ParamsParseError(f'argument {arg!r} is exclusive')
            
            if argument.mutex is not None:
                if argument.mutex in mmp:
                    raise ParamsParseError(
                        f'conflict arguments: {arg!r} and {mmp[argument.mutex]!r} '
                        f'mutex group({argument.mutex!r})'
                    )
                mmp[argument.mutex] = arg
            
            if argument.count == 0:
                self.add_option(argument, True)
                continue

            if argument.count == 1:
                self.add_option(argument, True)
                index += 1
                continue

            if argument.count == FLEX:
                auto = []
                while index < length:
                    arg = argv[index]
                    if arg in self:
                        break
                    auto.append(arg)
                    index += 1
                self.add_option(argument, auto)
                continue

            if argument.count == ALL:
                self.add_option(argument, argv[index:])
                break

            else:
                data = argv[index: index + argument.count]
                if len(data) != argument.count:
                    raise ParamsParseError(f'not enough arguments for {arg!r}')
                self.add_option(
                    argument,
                    argv[index: index + argument.count],
                )
                index += argument.count
        # for arg in self:
        #     if arg.required and arg.key not in self.__options:
        #         raise ParamsParseError(f'position argument {arg.short or arg.long!r} required')
        return self.__options, remains

    def __contains__(self, key: Union[str, Argument]) -> bool:
        
        if isinstance(key, str):
            return key in self.globals or key in self.optionals
        
        if isinstance(key, Argument):
            return key.short in self or key.long in self
        
        raise TypeError(f'unsupported type: {type(key)!r}, want "Argument" or "str"')

    def __getitem__(self, key) -> Argument:
        return self.optionals.get(key) or self.globals.get(key)
    
    def __iter__(self) -> Iterable[Argument]:

        for arg in self.optionals:
            yield arg

        for arg in self.globals:
            yield arg

    def __repr__(self) -> str:
        return f'{self.globals} {self.optionals}'


class CommandMeta(type):

    def __new__(cls, *args, **kwargs) -> object:
        self: object = super(CommandMeta, cls).__new__(cls, *args, **kwargs)
        self.subcommands = CommandMapping('Available Commands:')
        self.parent = None
        return self


class Command(metaclass=CommandMeta):

    name: Optional[str] = None
    desc: str = 'no command descriptor text'
    usage: Optional[str] = None
    epilog: Optional[str] = None
    version: Optional[str] = None
    alias: Optional[str] = None
    expects: Optional[List[str]] = None
    ARGUMENTS: List[Argument] = []

    def __init__(self, args: List[str], parser: Optional[Parser] = None) -> None:
        
        self.args: List[str] = args
        self.parser: Optional[Parser] = parser

    def pre_run(self, options: Options, remains: List[str]) -> bool:
        return True

    def run(self, options: Options, remains: List[str]) -> NoReturn:
        raise NotImplementedError(
            'subclass of "Command" must provide a '
            'run(options, remains) method'
        )     

    def post_run(self, options: Options, remains: List[str]) -> NoReturn:
        """"""

    @classmethod
    def add_subcommand(cls, name: str) -> Callable[[CmdType], CmdType]:
        return register(cls, name)

    @cached_property
    def parents(self) -> List[CmdType]:
        """ get parents command class list
         
        Returns: 
            [parent, ..., root]
        """
        ps: List[CmdType] = list()
        head = self.parent
        while head:
            ps.append(head)
            head = head.parent
        return ps
    
    def get_version(self) -> str:

        for p in self.parents[::-1]:
            if p.version is not None:
                self.version = p.version
                break

        names = [cls.name for cls in self.parents[::-1]]
        names.append(self.name)
        name: str = '-'.join(names)
        return f'{name} {self.version}'

    def generate_epilog(self) -> Optional[str]:

        if not self.epilog:
            commands: List[str] = list(map(lambda x: x.name, self.parents[::-1]))
            commands.append(self.name)
            if self.subcommands:
                commands.append('[command]')
            commands.append('-h/--help')
            self.epilog = 'use %r for more information about command.' % ' '.join(commands)
        return self.epilog
    
    def generate_usage(self) -> str:

        if not self.usage:
            self.usage = self.command_string

            if self.expects:
                self.usage += ' %s' % self.expected_string(*self.expects)
            if self.subcommands:
                self.usage += ' [%s] [argument ...] ARGS ...' % '|'.join(self.subcommands)
            else:
                self.usage += ' [%s] ARGS ...' % '|'.join(map(lambda x: x.short or x.long, self.parser))
        return self.usage
    
    @cached_property
    def command_string(self) -> str:
        parents_commands: List[str] = list(map(lambda x: x.name, self.parents[::-1]))
        return ' '.join((*parents_commands, self.name))
    
    @staticmethod
    @lru_cache(maxsize=64)
    def expected_string(*args) -> str:
        return ' '.join('<%s>' % expect for expect in args)
    
    def help(self) -> str:
        parts: List[str] = []
        header: List[str] = ['%s %s' % (self.command_string, self.desc)]
        usage: str = self.generate_usage()
        if usage:
            header.append('\n'.join(('Usage', '    %s' % usage)))
        parts.append('\n\n'.join(header))

        if self.alias:
            parts.append(
                '\n'.join(('Aliases', '    %s' % ', '.join(self.alias)))
            )
        
        if self.subcommands:
            parts.append(
                '\n'.join(self.subcommands.help())
            )

        if self.parser.optionals:
            parts.append(
                '\n'.join(self.parser.optionals.help())
            )
        
        if self.parser.globals:
            parts.append(
                '\n'.join(self.parser.globals.help())
            )
        
        epilog: str = self.epilog or self.generate_epilog()
        if epilog:
            parts.append(epilog)
        return '\n\n'.join(parts)

    @classmethod
    def match_command_class(cls, argv: List[str], index: int) -> Tuple[CmdType, int]:
        if argv[index:]:
            sub_class: Optional[Command] = cls.subcommands.match_command(argv[index])
            if sub_class:
                return sub_class.match_command_class(argv, index + 1)
        return cls, index

    def _match_expects(self, options: Options, remains: List[Any]) -> str:

        if self.expects:
            index: int = len(self.expects) - len(remains)
            if index > 0:
                expected_string: str = self.expected_string(*self.expects[0 - index:])
                return f'{self.command_string!r} cannot found expected argument {expected_string!r}'
            for expect in self.expects:
                options[expect] = remains.pop(0)

    def __call__(self, options: Options, remains: List[str]) -> bool:

        if not self.pre_run(options, remains):
            return
        try:
            self.run(options, remains)
        except Exception as exc:
            raise exc from None
        finally:
            self.post_run(options, remains)
    
    def __repr__(self) -> str:
        return f'{type(self).__name__}({self.name}, {self.args})'

    __str__ = __repr__


class App(Command):
    """ Application parent class """

    GLOBAL_ARGUMENTS: List[Argument] = []

    def __init__(self, args: List[str]) -> None:
        super(App, self).__init__(args[1:])
        if self.name is None:
            self.name = self.__class__.name = op.basename(args[0])
        self.parser = self.create_parser()
        self.command: Optional[Command] = None

    def create_parser(self) -> Parser:
        """ create a command line arguments parser """
        parser: Parser = Parser()
        parser.add_global_args(
            Argument(
                '-h', '--help',
                docs='print help text',
                default=False,
                count=0,
                exclusive=True,
            ),
            Argument(
                '-v', '--version',
                docs='print version number',
                default=False,
                count=0,
                exclusive=True,
            ),
            *self.GLOBAL_ARGUMENTS
        )
        return parser
    
    def exec(self, *args, **kwargs) -> NoReturn:
        """

        Args:
            *args:
            **kwargs:

        Returns:

        """

        try:
            self._handle(*args, **kwargs)
        except ParamsParseError as exc:
            check_error(exc)
            # FIXME print notice docs
        except SitterError as exc:
            check_error(exc)

    def _handle(self, *args, **kwargs) -> None:
        """

        Args:
            *args:
            **kwargs:

        Returns:

        """

        command_class, index = self.match_command_class(self.args, 0)
        self.command: Command = (
            self if isinstance(self, command_class)
            else command_class(self.args[index:], self.parser)
        )

        # add command arguments
        self.parser.add_args(*self.command.ARGUMENTS)

        # check whether the type is correct and whether the key
        # conflicts with the parameter
        if self.command.expects:
            for expect in self.command.expects or []:
                if not isinstance(expect, str):
                    raise TypeError(
                        f'expect want str but get {type(expect).__name__!r}'
                    )
                if self.parser.has_key(expect):
                    raise ArgumentError(
                        f'conflict argument and expects: {expect!r}'
                    )

        # parse options and remains
        options, remains = self.parser.parse_argv(self.command.args)

        # check options
        check_error(self.check_options(options, remains))

        self.command(options, remains)

    def check_options(self, options: Options, remains: List[str]) -> str:

        if options.get('help'):
            print(self.help(), file=sys.stderr)
            sys.exit(1)

        if options.get('version'):
            print(self.get_version(), file=sys.stderr)
            sys.exit(1)

        # TODO optimize logic (cached default arguments)
        for arg in self.parser:
            if arg.required and arg.key not in options:
                return f'position argument {arg.short or arg.long!r} required'

            if arg.default is not empty and arg.key not in options:
                options[arg.key] = arg.default

        return self.command._match_expects(options, remains)


def register(parent_class: CmdType, subcommand: str) -> Callable:
    """ register subcommand to parent_command

    Args:
        parent_class:
        subcommand:

    Returns:

    """

    if not subcommand or not isinstance(subcommand, str) or not subcommand.isprintable():
        raise ValueError(
            'subcommand must be a printable string'
        )

    if not issubclass(parent_class, Command):
        raise TypeError(
            'parent_class must derive from "Command"'
        )

    def wrapper(cls: CmdType) -> Callable:

        if not issubclass(cls, Command):
            raise TypeError('command must derive from "Command"')

        if not isinstance(cls.expects, (Iterable, NoneType)):
            raise TypeError(
                f'{cls.__name__}.alias should be iterable not {type(cls.expects)!r}'
            )
        
        cls.parent = parent_class
        if not cls.name:
            cls.name = subcommand
        parent_class.subcommands.add_command(cls)
        return cls

    return wrapper
