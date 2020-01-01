from __future__ import annotations
from typing import *

from unicodedata import category
from functools import wraps
from itertools import zip_longest
from enum import Enum


T = TypeVar('T')
U = TypeVar('U')
Parser = Callable[[str], Tuple[T, str]]


class ParseException(BaseException):
    pass


def pure(r: T) -> Parser[T]:
    @wraps(pure)
    def _parser(s: str) -> Tuple[T, str]:
        return r, s
    return _parser


def char(_input: str) -> Tuple[str, str]:
    if len(_input) > 0:
        return _input[0], _input[1:]
    raise ParseException(_input)


class Const(object):
    def __init__(self, const: str) -> None:
        self.const = const

    def __call__(self, s: str) -> Tuple[str, str]:
        s_orig = s
        for c1 in self.const:
            c2, s = char(s)
            if c1.lower() != c2.lower():
                raise ParseException(s_orig, self.const)
        return self.const, s

    def __repr__(self) -> str:
        return f"Const({self.const!r})"


const = Const


class Options(Generic[T]):
    def __init__(self, *parsers: Parser[T]) -> None:
        self.parsers = parsers

    def __call__(self, s: str) -> Tuple[T, str]:
        s_orig = s
        last_exc: Optional[ParseException]
        last_exc = None
        for parser in self.parsers:
            try:
                return parser(s)
            except ParseException as exc:
                last_exc = exc
        if last_exc:
            raise last_exc
        raise ParseException(s_orig)

    def __repr__(self) -> str:
        return f"Options{self.parsers!r}"


options = Options


class Chain(Generic[T]):
    def __init__(self, *parsers: Parser[T]) -> None:
        self.parsers = parsers

    def __call__(self, s: str) -> Tuple[List[T], str]:
        rets = []
        for parser in self.parsers:
            res, s = parser(s)
            rets.append(res)
        return rets, s

    def __repr__(self) -> str:
        return f"Chain{self.parsers!r}"


chain = Chain


class Optional(Generic[T]):
    def __init__(self, parser: Parser[T]) -> None:
        self.parser = parser

    def __call__(self, s: str) -> Tuple[Optional[T], str]:
        try:
            return self.parser(s)
        except ParseException:
            pass
        return None, s

    def __repr__(self) -> str:
        return f"Optional({self.parser!r})"


optional = Optional


class Some(object):
    def __init__(self, parser: Parser[T]) -> None:
        self._many_parser = Many(parser)
        self.parser = parser

    def __call__(self, s: str) -> Tuple[List[T], str]:
        ret, s = self.parser(s)
        res, s = self._many_parser(s)
        return [ret] + res, s

    def __repr__(self) -> str:
        return f"Some({self.parser!r})"


some = Some


class Many(object):
    def __init__(self, parser: Parser[T]) -> None:
        self.parser = parser

    def __call__(self, s: str) -> Tuple[List[T], str]:
        ret = []
        while True:
            try:
                res, s = self.parser(s)
            except ParseException:
                break
            else:
                ret.append(res)
        return ret, s

    def __repr__(self) -> str:
        return f"Many({self.parser!r})"


many = Many


def failure(s: str) -> Tuple[T, str]:
    raise ParseException(s)


def eof(s: str) -> Tuple[None, str]:
    if len(s) == 0:
        return None, s
    raise ParseException(s)


class Satisfy(object):
    def __init__(self, cond: Callable[[str], bool]):
        self.cond = cond

    def __call__(self, s: str) -> Tuple[str, str]:
        x, s_new = char(s)
        if not self.cond(x):
            raise ParseException(s)
        return x, s_new

    def __repr__(self) -> str:
        return f"Satisfy({self.cond!r})"


satisfy = Satisfy


def is_space(c: str) -> bool:
    return c in "\r\n\t "


def is_letter(c: str) -> bool:
    return category(c)[0] == 'L'


def is_number(c: str) -> bool:
    return category(c)[0] == 'N'


def somewhere(parser: Parser[T]) -> Parser[T]:
    def _parser(s: str) -> Tuple[T, str]:
        while s:
            try:
                res, s = parser(s)
            except ParseException:
                s = s[1:]
            else:
                return res, s
        raise ParseException(s)
    return _parser


def lookahead(parser: Parser[T]) -> Parser[T]:
    def _parser(s: str) -> Tuple[T, str]:
        res, _ = parser(s)
        return res, s
    return _parser


def name(name: str, parser: Parser[T]) -> Parser[T]:
    parser.__name__ = parser.__qualname__ = name
    return parser


spaces = many(satisfy(is_space))


class Token(object):
    def __init__(self, parser: Parser[T]):
        self.parser = parser

    def __call__(self, s: str) -> Tuple[T, str]:
        ret, s = self.parser(s)
        _, s = spaces(s)
        return ret, s

    def __repr__(self) -> str:
        return f"Token({self.parser!r})"


token = Token


def one_of(chars: str) -> Parser[str]:
    return satisfy(lambda x: x in chars)


class SepBy(object):
    def __init__(self, parser: Parser[T], sep: Parser[U], inject: bool = False) -> None:
        self.parser = parser
        self.sep = sep
        self.inject = inject

    def __call__(self, s: str) -> Tuple[List[T], str]:
        res, s = self.parser(s)
        ret = [res]
        while True:
            try:
                res1, s1 = self.sep(s)
                res, s = self.parser(s1)
            except ParseException:
                break
            if self.inject:
                ret.append(res1)
            ret.append(res)
        return ret, s

    def __repr__(self) -> str:
        return f"SepBy({self.parser!r}, {self.sep!r})"


sep_by = SepBy


class PMap(object):
    def __init__(self, f: Callable[[T], U], parser: Parser[T]) -> None:
        self.f = f
        self.parser = parser

    def __call__(self, s: str) -> Tuple[U, str]:
        res, s = self.parser(s)
        return self.f(res), s

    def __repr__(self) -> str:
        return f"PMap({self.f!r}, {self.parser!r})"


pmap = PMap


def mark(m: U, parser: Parser[T]) -> Parser[Tuple[U, T]]:
    return pmap(lambda r: (m, r), parser)


def forward(resolve: Callback[[], T]) -> T:
    def f(*args, **kwargs):
        return resolve()(*args, **kwargs)
    return f


# Tokens
from_lit = token(const("from"))
action_lit = token(const("action"))
accept_lit = token(const("accept"))
noun_lit = pmap("".join, token(some(options(satisfy(is_letter),
                                            satisfy(is_number),
                                            one_of(":-_")))))
announce_lit = token(const("announce"))
to_lit = token(const("to"))
op_lit = token(options(const("<<="),
                       const(">>="),
                       const("+="),
                       const("-="),
                       const("*="),
                       const("/="),
                       const(".="),
                       const("!="),
                       const("<="),
                       const(">="),
                       const("=="),
                       const("="),
                       const("<"),
                       const(">")))
hex_lit = pmap("".join, token(some(one_of("abcdefABCDEF0123456789"))))
filter_lit = noun_lit
any_lit = token(const("any"))
protocol_lit = token(const("protocol"))
into_lit = token(const("into"))
caret_lit = token(const("^"))
minus_lit = token(const("-"))
plus_lit = token(const("+"))
slash_lit = token(const("/"))
num_lit = pmap(int, pmap("".join, token(some(satisfy(is_number)))))
comma_lit = token(const(","))
semicolon_lit = token(const(";"))
dot_lit = token(const("."))
colon_lit = token(const(':'))
afi_lit = token(const("afi"))
lbr_lit = token(const('{'))
rbr_lit = token(const('}'))
lb_lit = token(const("["))
rb_lit = token(const("]"))
lt_lit = token(const("<"))
gt_lit = token(const(">"))
pipe_lit = token(const("|"))
lpar_lit = token(const("("))
rpar_lit = token(const(")"))
qm_lit = token(const("$"))
ast_lit = token(const("*"))
plus_lit = token(const("+"))
qm_lit = token(const("?"))
tilde_lit = token(const("~"))
afi_value_lit = token(options(const("ipv4.unicast"),
                              const("ipv4.multicast"),
                              const("ipv4"),
                              const("ipv6.unicast"),
                              const("ipv6.multicast"),
                              const("ipv6"),
                              const("any"),
                              const("any.unicast"),
                              const("any.multicast")))
except_lit = token(const("except"))
refine_lit = token(const("refine"))
peer_as_lit = token(const("PeerAS"))
and_lit = token(const("AND"))
or_lit = token(const("OR"))
not_lit = token(const("NOT"))
as_lit = pmap(lambda r: r[0] + str(r[1]), chain(const("AS"), num_lit))
as_set_lit = pmap(lambda r: r[0] + r[1], chain(const("AS-"), noun_lit))
peering_set_lit = pmap(lambda r: r[0] + r[1], chain(const("PRNG-"), noun_lit))
router_lit = pmap(lambda r: r[0] + r[1], chain(const("RTRS-"), noun_lit))
dollar_lit = token(const("$"))
upon_lit = token(const("upon"))
static_lit = token(const("static"))
at_lit = token(const("at"))
double_colon_lit = token(const("::"))
have_components_lit = token(const("HAVE-COMPONENTS"))
exclude_lit = token(const("EXCLUDE"))


# Addresses

ipv4_address_clause = chain(num_lit, dot_lit,
                            num_lit, dot_lit,
                            num_lit, dot_lit,
                            num_lit)
ipv6_address_clause = token(sep_by(
    many(one_of("abcdefABCDEF0123456789")),
    options(const("::"), const(":")),
    True))

address_clause = options(
    ipv4_address_clause,
    ipv6_address_clause)

# Prefix sets
prefix_range_clause = chain(caret_lit,
                            options(minus_lit,
                                    plus_lit,
                                    chain(num_lit, minus_lit, num_lit),
                                    num_lit))
prefix_clause = chain(address_clause,
                      slash_lit,
                      num_lit,
                      optional(prefix_range_clause))
prefix_set_clause = chain(lbr_lit,
                          optional(sep_by(prefix_clause, comma_lit)),
                          rbr_lit,
                          optional(prefix_range_clause))

# Values
value_clause = forward(lambda: value_clause)
value_set_clause = chain(lbr_lit,
                         optional(sep_by(value_clause, comma_lit)),
                         rbr_lit)
value_int_clause = chain(num_lit, colon_lit, num_lit)
value_clause = options(value_set_clause,
                       value_int_clause,
                       noun_lit)

# Actions
action_call_args_clause = sep_by(value_clause, comma_lit)
action_call_clause = chain(sep_by(noun_lit, dot_lit), lpar_lit,
                           optional(action_call_args_clause), rpar_lit)
action_op_clause = chain(noun_lit, op_lit, value_clause)
action_clause = some(chain(options(action_call_clause, action_op_clause),
                           semicolon_lit))

# Filters

as_set_entry_clause = options(
    chain(as_lit, minus_lit, as_lit),
    as_lit,
    chain(num_lit, minus_lit, num_lit),
    num_lit)
as_set_clause = chain(lb_lit, optional(caret_lit),
                      many(as_set_entry_clause), rb_lit)

as_regex_op_clause = options(
    ast_lit,
    plus_lit,
    qm_lit,
    chain(lbr_lit, num_lit, rbr_lit),
    chain(lbr_lit, num_lit, comma_lit, num_lit, rbr_lit),
    chain(lbr_lit, num_lit, comma_lit, rbr_lit),
    chain(tilde_lit, ast_lit),
    chain(tilde_lit, plus_lit),
    chain(tilde_lit, lbr_lit, num_lit, rbr_lit),
    chain(tilde_lit, lbr_lit, num_lit, comma_lit, num_lit, rbr_lit),
    chain(tilde_lit, lbr_lit, num_lit, comma_lit, rbr_lit))

as_regex_clause = forward(lambda: as_regex_clause)
as_regex_expr_clause = chain(options(
    as_lit,
    as_set_lit,
    as_set_clause,
    dot_lit,
    dollar_lit,
    caret_lit,
    chain(lpar_lit, as_regex_clause, rpar_lit)),
    many(as_regex_op_clause))
as_regex_clause = sep_by(
    many(as_regex_expr_clause),
    pipe_lit)

filter_rs_clause = chain(noun_lit, optional(prefix_range_clause))

filter_clause = forward(lambda: filter_clause)
filter_expr_clause = options(
    chain(lpar_lit, filter_clause, rpar_lit),
    any_lit,
    peer_as_lit,
    action_call_clause,
    filter_rs_clause,
    prefix_set_clause,
    chain(lt_lit, as_regex_clause, gt_lit))
filter_clause = sep_by(
    chain(optional(not_lit), filter_expr_clause),
    options(and_lit, or_lit, pmap(
        lambda s: 'OR', lookahead(filter_expr_clause))),
    inject=True)


# Peering specification

as_expr_clause = forward(lambda: as_expr_clause)
as_expr_clause = sep_by(
    options(as_lit, as_set_lit, chain(lbr_lit, as_expr_clause, rbr_lit)),
    options(and_lit, or_lit, except_lit),
    True)

router_expr_clause = forward(lambda: router_expr_clause)
router_expr_clause = sep_by(
    options(address_clause, router_lit,
            chain(lbr_lit, router_expr_clause, rbr_lit)),
    options(and_lit, or_lit, except_lit),
    True)

peering_clause = options(
    chain(as_expr_clause,
          optional(router_expr_clause),
          optional(chain(at_lit, router_expr_clause))),
    peering_set_lit)

# Import
import_factor_clause = chain(some(chain(from_lit,
                                        peering_clause,
                                        optional(chain(action_lit,
                                                       action_clause)))),
                             accept_lit,
                             filter_clause,
                             optional(semicolon_lit))

import_term_clause = options(import_factor_clause,
                             chain(lbr_lit, many(import_factor_clause), rbr_lit))

import_expression_clause = forward(lambda: import_expression_clause)
import_expression_clause = sep_by(
    import_term_clause,
    options(except_lit, refine_lit),
    inject=True)

import_clause = chain(optional(chain(protocol_lit,
                                     noun_lit)),
                      optional(chain(into_lit,
                                     noun_lit)),
                      import_expression_clause,
                      eof)

# Export
export_factor_clause = chain(some(chain(to_lit,
                                        peering_clause,
                                        optional(chain(action_lit,
                                                       action_clause)))),
                             announce_lit,
                             filter_clause)

export_term_clause = options(export_factor_clause,
                             chain(lbr_lit, some(export_factor_clause), rbr_lit))

export_expression_clause = forward(lambda: export_expression_clause)
export_expression_clause = options(
    chain(export_term_clause, except_lit, export_expression_clause),
    chain(export_term_clause, refine_lit, export_expression_clause),
    export_term_clause
)

export_clause = chain(optional(chain(protocol_lit,
                                     noun_lit)),
                      optional(chain(into_lit,
                                     noun_lit)),
                      export_expression_clause,
                      eof)

# Inject
condition_clause = sep_by(options(
    static_lit,
    chain(have_components_lit, prefix_set_clause),
    chain(exclude_lit, prefix_set_clause),
), options(and_lit, or_lit), True)

inject_clause = chain(many(chain(at_lit, router_expr_clause)),
                      optional(chain(action_lit, action_clause)),
                      optional(chain(upon_lit, condition_clause)))


# Multiprotocol
afi_clause = chain(afi_lit, afi_value_lit)

mp_import_clause = chain(afi_clause, import_clause)
mp_export_clause = chain(afi_clause, export_clause)
