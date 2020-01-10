from __future__ import annotations
from typing import *

import unicodedata


# S denotes the type of a token in the input sequence
S = TypeVar('S')

# T, U are the type variables for produced values
T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')


class Forward(Generic[T]):
    def __init__(self, _resolve: T) -> None:
        self._resolve = _resolve

    @no_type_check
    def __call__(self, *args, **kwargs):
        return self._resolve()(*args, **kwargs)

    def __repr__(self):
        try:
            resolved = self._resolve()
        except NameError:
            return f'<Forward unresolved {self._resolve!r}>'
        else:
            return f'Forward({resolved!r})'


# A map that maps a sequence of tokens of type S to a tuple that consists of
# a produced value T and a remaining sequence of tokens of type S is a parser.
Parser = Callable[[Sequence[S]], Tuple[T, Sequence[S]]]


class ParseException(Exception, Generic[S]):
    def __init__(self, got: Sequence[S], expected: str, rule: Any = None) -> None:
        self.got = got
        self.expected = expected
        if rule is not None:
            rule = str(rule)
        self.rule = rule

# Generic combinators


class Pure(Generic[S, T]):
    def __init__(self, r: T):
        self.r = r

    def __call__(self, seq: Sequence[S]) -> Tuple[T, Sequence[S]]:
        return self.r, seq

    def __repr__(self):
        return f"Pure({self.r!r})"


def any(seq: Sequence[S]) -> Tuple[S, Sequence[S]]:
    try:
        return seq[0], seq[1:]
    except IndexError:
        pass
    raise ParseException('<eof>', '<any>', 'any')


class _EOF(object):
    def __call__(self, seq: Sequence[S]) -> Tuple[None, Sequence[S]]:
        try:
            got = seq[0]
        except IndexError:
            return None, seq
        else:
            raise ParseException(seq, '<eof>', 'eof')

    def __repr__(self):
        return f"eof"


eof = _EOF()


class Chain(Generic[S, T]):
    parsers: Sequence[Parser[S, T]]

    def __init__(self, *parsers: Parser[S, T]) -> None:
        self.parsers = tuple(parsers)

    def __call__(self, seq: Sequence[S]) -> Tuple[List[T], Sequence[S]]:
        ret = []
        for parser in self.parsers:
            res, seq = parser(seq)
            ret.append(res)
        return ret, seq

    def __repr__(self):
        return f"Chain{self.parsers!r}"


class Options(Generic[S, T]):
    parsers: Sequence[Parser[S, T]]

    def __init__(self, *parsers: Parser[S, T]) -> None:
        self.parsers = tuple(parsers)

    def __call__(self, seq: Sequence[S]) -> Tuple[T, Sequence[S]]:
        for parser in self.parsers:
            try:
                return parser(seq)
            except ParseException:
                pass
        raise ParseException(seq, '<options>', self)

    def __repr__(self):
        return f"Options{self.parsers!r}"


class OptionsAmbig(Generic[S, T]):
    parsers: Sequence[Parser[S, T]]

    def __init__(self, *parsers: Parser[S, T]) -> None:
        self.parsers = parsers

    def __call__(self, seq: Sequence[S]) -> Tuple[T, Sequence[S]]:
        ret = []
        for parser in self.parsers:
            try:
                res, seq_new = parser(seq)
                pass
            except ParseException:
                pass
            else:
                ret.append((res, seq_new))
        if not ret or len(ret) > 1:
            print(ret)
            raise ParseException(seq, '<options ambiguous>', self)
        return ret.pop()

    def __repr__(self):
        return f"OptionsAmbig{self.parsers!r}"


class Satisfy(Generic[S, T]):
    function: Callable[[S], bool]

    def __init__(self, function: Callable[[S], bool], readable: Optional[str] = None) -> None:
        self.function = function
        self.readable = readable

    def __call__(self, seq: Sequence[S]) -> Tuple[S, Sequence[S]]:
        r, seq_new = any(seq)
        if not self.function(r):
            raise ParseException(seq, f'<satisfy {self.function!r}>', self)
        return r, seq_new

    def __repr__(self):
        readable: Union[str, Callable[[S], bool], None]
        readable = self.readable
        if readable is None:
            readable = self.function
        return f"Satisfy({readable!r})"


class SatisfyP(Generic[S, T]):
    function: Callable[[T], bool]
    parser: Parser[S, T]
    readable: Optional[str]

    def __init__(self, function: Callable[[T], bool],
                 parser: Parser[S, T], readable: Optional[str] = None) -> None:
        self.function = function
        self.readable = readable
        self.parser = parser

    def __call__(self, seq: Sequence[S]) -> Tuple[S, Sequence[S]]:
        r, seq_new = self.parser(seq)
        if not self.function(r):
            raise ParseException(seq, repr(self), self)
        return r, seq_new

    def __repr__(self):
        readable = Union[str, Callable[[S], bool], None]
        readable = self.readable
        if readable is None:
            readable = self.function
        return f"SatisfyP({readable!r}, {self.parser!r})"


class Many(Generic[S, T]):
    parser: Parser[S, T]

    def __init__(self, parser: Parser[S, T]) -> None:
        self.parser = parser

    def __call__(self, seq: Sequence[S]) -> Tuple[List[T], Sequence[S]]:
        ret = []
        try:
            while True:
                res, seq = self.parser(seq)
                ret.append(res)
        except ParseException:
            pass
        return ret, seq

    def __repr__(self):
        return f"Many({self.parser!r})"


class Some(Generic[S, T]):
    parser: Parser[S, T]

    def __init__(self, parser: Parser[S, T]) -> None:
        self.parser = parser

    def __call__(self, seq: Sequence[S]) -> Tuple[List[T], Sequence[S]]:
        res, seq = self.parser(seq)
        ret = [res]
        try:
            while True:
                res, seq = self.parser(seq)
                ret.append(res)
        except ParseException:
            pass
        return ret, seq

    def __repr__(self):
        return f"Some({self.parser!r})"


class Range(Generic[S, T]):
    range: Sequence[int]
    parser: Parser[S, T]

    def __init__(self, parser: Parser[S, T], range_: Sequence[int]) -> None:
        self.parser = parser
        if isinstance(range_, (list, set, tuple)):
            range_ = sorted(range_)
        self.range = range_

    def __call__(self, seq: Sequence[S]) -> Tuple[List[T], Sequence[S]]:
        ret = []
        seq_orig = seq
        for n in self.range[::-1]:
            seq = seq_orig
            try:
                ret = []
                for i in range(n):
                    res, seq = self.parser(seq)
                    ret.append(res)
            except ParseException:
                pass
            else:
                return ret, seq
        raise ParseException(seq_orig, repr(self), self)

    def __repr__(self):
        return f"Range({self.parser!r}, {self.range!r})"


class FailIf(Generic[S, T]):
    parser: Parser[S, T]

    def __init__(self, parser: Parser[S, T]) -> None:
        self.parser = parser

    def __call__(self, seq: Sequence[S]) -> Tuple[None, Sequence[S]]:
        try:
            _, seq_new = self.parser(seq)
        except ParseException:
            return None, seq
        raise ParseException(seq, f'<not {self.parser!r}>', self)

    def __repr__(self):
        return f"FailIf({self.parser!r})"


class Lookahead(Generic[S, T]):
    parser: Parser[S, T]

    def __init__(self, parser: Parser[S, T]) -> None:
        self.parser = parser

    def __call__(self, seq: Sequence[S]) -> Tuple[T, Sequence[S]]:
        res, _ = self.parser(seq)
        return res, seq

    def __repr__(self):
        return f"Lookahead({self.parser!r})"


class SepBy(Generic[S, T, U]):
    parser: Parser[S, T]
    separator: Parser[S, U]
    inject: bool

    def __init__(self, parser: Parser[S, T], separator: Parser[S, U],
                 inject: bool = False) -> None:
        self.parser = parser
        self.separator = separator
        self.inject = inject

    def __call__(self, seq: Sequence[S]) -> Tuple[List[T], Sequence[S]]:
        res, seq = self.parser(seq)
        ret = [res]
        try:
            while True:
                res, seq = self.separator(seq)
                if self.inject:
                    ret.append(res)
                res, seq = self.parser(seq)
                ret.append(res)
        except ParseException:
            pass
        return ret, seq

    def __repr__(self):
        return f"SepBy({self.parser!r}, {self.separator!r})"


class Const(Generic[S]):
    constant: Sequence[S]

    def __init__(self, constant: Sequence[S]) -> None:
        self.constant = constant

    def __call__(self, seq: Sequence[S]) -> Tuple[Sequence[S], Sequence[S]]:
        seq_orig = seq
        for c in self.constant:
            try:
                if c != seq[0]:
                    raise ParseException(
                        seq_orig, f'<const {self.constant!r}>', self)
            except IndexError:
                raise ParseException(
                    seq_orig, f'<const {self.constant!r}>', self)
            seq = seq[1:]
        return self.constant, seq

    def __repr__(self):
        return f'Const({self.constant!r})'


class PMap(Generic[S, T, U]):
    f: Callable[[T], U]
    parser: Parser[S, T]

    def __init__(self, f: Callable[[T], U], parser: Parser[S, T]) -> None:
        self.f = f
        self.parser = parser

    def __call__(self, seq: Sequence[S]) -> Tuple[U, Sequence[S]]:
        res, seq = self.parser(seq)
        return self.f(res), seq

    def __repr__(self):
        return f'PMap({self.f!r}, {self.parser!r})'


class Parens(Generic[S, T, U, V]):
    parser: Parser[S, T]
    lparen: Parser[S, U]
    rparen: Parser[S, V]

    def __init__(self, parser: Parser[S, T], lparen: Parser[S, U],
                 rparen: Parser[S, V]) -> None:
        self.parser = parser
        self.lparen = lparen
        self.rparen = rparen

    def __call__(self, seq: Sequence[S]) -> Tuple[T, Sequence[S]]:
        _, seq = self.lparen(seq)
        res, seq = self.parser(seq)
        _, seq = self.rparen(seq)
        return res, seq

    def __repr__(self):
        return f'Parens({self.parser!r}, {self.lparen!r}, {self.rparen!r})'


def chain_map(f: Callable[[List[T]], U], *parsers: Parser[S, T]) -> Parser[S, U]:
    chain_parser = chain(*parsers)

    def _parser(seq: Sequence[S]) -> Tuple[U, Sequence[S]]:
        res, seq = chain_parser(seq)
        return f(res), seq
    return _parser


class OneOf(Generic[S]):
    set: Sequence[S]

    def __init__(self, set_: Sequence[S]) -> None:
        self.set = set_

    def __call__(self, seq: Sequence[S]) -> Tuple[S, Sequence[S]]:
        seq_orig = seq
        try:
            res, seq = seq[0], seq[1:]
        except IndexError:
            raise ParseException(seq_orig, f'<one_of {self.set!r}>', self)
        if res not in self.set:
            raise ParseException(seq_orig, f'<one_of {self.set!r}>', self)
        return res, seq

    def __repr__(self):
        return f'OneOf({self.set!r})'

# str-specific combinators


alpha = Satisfy(str.isalpha, "str.isalpha")
alnum = Satisfy(str.isalnum, "str.isalnum")
space = Satisfy(str.isspace, "str.isspace")
numeric = Satisfy(str.isnumeric, "str.isnumeric")


def optional(parser): return Options(parser, Pure(None))


class Token(Generic[T]):
    parser: Parser[str, T]

    def __init__(self, parser: Parser[str, T]) -> None:
        self.parser = parser

    def __call__(self, seq: Sequence[str]) -> Tuple[T, Sequence[str]]:
        res: T
        res, seq = self.parser(seq)
        try:
            while True:
                _, seq = space(seq)
        except ParseException:
            pass
        return res, seq

    def __repr__(self):
        return f"Token({self.parser!r})"


class StrConst(Const[str]):
    def __init__(self, constant: Sequence[str], case_insensitive=True) -> None:
        super().__init__(constant)
        self.case_insensitive = case_insensitive

    def __call__(self, seq: Sequence[str]) -> Tuple[Sequence[str], Sequence[str]]:
        seq_orig = seq
        for c in self.constant:
            try:
                cc = seq[0].lower() if self.case_insensitive else seq[0]
                c = c.lower() if self.case_insensitive else c
                if c != cc:
                    raise ParseException(
                        seq_orig,
                        f'<str_const {self.constant!r} {self.case_insensitive}',
                        self)
            except IndexError:
                raise ParseException(
                    seq_orig,
                    f'<str_const {self.constant!r} {self.case_insensitive}',
                    self)
            seq = seq[1:]
        return self.constant, seq

    def __repr__(self):
        return f'StrConst({self.constant!r}, {self.case_insensitive!r})'


class Parser(Generic[S, T]):
    parser: Parser[S, T]
    _name: Optional[str] = None

    def __init__(self, parser: Parser[S, T], name: Optional[str] = None) -> None:
        self.parser = parser
        self._name = name

    def __call__(self, seq: Sequence[S]) -> Parser[S, T]:
        return self.parser(seq)

    def __repr__(self):
        return self._name or self.parser.__name__
