from __future__ import annotations
from typing import *

from unicodedata import category
from functools import wraps
from itertools import zip_longest
from enum import Enum
from pprint import pprint


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


def flatten(l: Union[str, int, List[Any]]) -> str:
    if isinstance(l, list):
        return "".join(flatten(e) for e in l)
    elif l is None:
        return ""
    return str(l)


# Tokens
from_lit = token(const("from"))
action_lit = token(const("action"))
accept_lit = token(const("accept"))
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
dollar_lit = token(const("$"))
upon_lit = token(const("upon"))
static_lit = token(const("static"))
at_lit = token(const("at"))
have_components_lit = token(const("HAVE-COMPONENTS"))
exclude_lit = token(const("EXCLUDE"))


class ObjectRef(object):
    parser = token(chain(satisfy(is_letter), many(options(
        satisfy(is_letter),
        satisfy(is_number),
        one_of(":-_")))))

    def __init__(self, primary_key, classes=None):
        self.primary_key = primary_key
        if classes is not None:
            classes = set(classes)
        self.classes = classes

    def __repr__(self):
        return f"{self.__class__.__name__}({self.primary_key!r}, {self.classes!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(flatten(r)), s

    def __str__(self):
        return self.primary_key


class ASRef(ObjectRef):
    parser = chain(const("AS"), num_lit)

    def __init__(self, primary_key, classes={"aut-num"}):
        super().__init__(primary_key, classes)

    def __int__(self):
        return int(self.primary_key[2:])


class ASSetRef(ObjectRef):
    parser = chain(const("AS-"), ObjectRef.parser)

    def __init__(self, primary_key, classes={"as-set"}):
        super().__init__(primary_key, classes)


class PeeringSetRef(ObjectRef):
    parser = chain(const("PRNG-"), ObjectRef.parser)

    def __init__(self, primary_key, classes={"peering-set"}):
        super().__init__(primary_key, classes)


class RouterRef(ObjectRef):
    parser = chain(const("RTRS-"), ObjectRef.parser)

    def __init__(self, primary_key, classes={"inet-rtr", "rtr-set"}):
        super().__init__(primary_key, classes)


class IPv4Address(object):
    parser = token(sep_by(some(satisfy(is_number)),
                          const("."),
                          inject=True))

    def __init__(self, address):
        self.address = address

    @classmethod
    def parse(cls, s):
        p, s = cls.parser(s)
        return cls(flatten(p)), s

    def __repr__(self):
        return f"IPv4Address({self.address!r})"

    def __str__(self):
        return self.address


hexdigit_parser = one_of("abcdefABCDEF0123456789")


class IPv6Address(object):
    hextet_parser = options(
        chain(hexdigit_parser, hexdigit_parser,
              hexdigit_parser, hexdigit_parser),
        chain(hexdigit_parser, hexdigit_parser, hexdigit_parser),
        chain(hexdigit_parser, hexdigit_parser),
        hexdigit_parser)
    full_parser = sep_by(hextet_parser, const(":"), True)
    parser = token(options(
        chain(optional(full_parser), const("::"), optional(full_parser)),
        chain(hextet_parser, const(":"), full_parser)))

    def __init__(self, address):
        self.address = address

    @classmethod
    def parse(cls, s):
        p, s = cls.parser(s)
        return cls(flatten(p)), s

    def __repr__(self):
        return f"IPv6Address({self.address!r})"

    def __str__(self):
        return self.address


ip_address_parser = options(IPv4Address.parse, IPv6Address.parse)


class PrefixRange(object):
    parser = chain(caret_lit,
                   options(minus_lit,
                           plus_lit,
                           chain(num_lit, minus_lit, num_lit),
                           num_lit))

    def __init__(self, range_):
        self.range = range_

    @classmethod
    def parse(cls, s):
        p, s = cls.parser(s)
        return cls(p), s

    def __repr__(self):
        return f"PrefixRange({self.range!r})"


class PrefixSet(object):
    prefix_parser = chain(ip_address_parser,
                          slash_lit,
                          num_lit,
                          optional(PrefixRange.parse))
    parser = chain(lbr_lit,
                   optional(sep_by(prefix_parser, comma_lit)),
                   rbr_lit,
                   optional(PrefixRange.parse))

    def __init__(self, prefixes=set(), range_=None):
        self.prefixes = set(prefixes)
        self.range_ = range_

    @classmethod
    def parse(cls, s):
        parsed, s = cls.parser(s)
        prefixes = parsed[1]
        if prefixes is None:
            prefixes = ()
        global_range = parsed[3]
        return cls(((prefix[0], prefix[2], prefix[3]) for prefix in prefixes),
                   global_range), s

    def __repr__(self):
        return f"PrefixSet({self.prefixes!r}, {self.range_!r})"


# Values
value_parser = forward(lambda: value_parser)


class ValueSet(object):
    parser = chain(lbr_lit,
                   optional(sep_by(value_parser, comma_lit)),
                   rbr_lit)

    def __init__(self, values=set()):
        self.values = set(values)

    def __repr__(self):
        return f"ValueSet({self.values!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        r = r[1]
        if r is None:
            r = ()
        return cls(r), s


# TODO Implement A:B integer representation
value_parser = options(ValueSet.parse,
                       num_lit,
                       ObjectRef.parse)

# Actions


class ActionCall(object):
    args_parser = sep_by(value_parser, comma_lit)
    parser = chain(sep_by(ObjectRef.parse, dot_lit), lpar_lit,
                   optional(args_parser), rpar_lit)

    def __init__(self, func, args):
        self.func = func
        self.args = args

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[1] or ()), s

    def __repr__(self):
        return f"ActionCall({self.func!r}, {self.args!r})"


class ActionOp(object):
    parser = chain(ObjectRef.parse, op_lit, value_parser)

    def __init__(self, attr, operator, value):
        self.attr = attr
        self.operator = operator
        self.value = value

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(*r), s

    def __repr__(self):
        return f"ActionOp({self.attr!r}, {self.operator!r}, {self.value!r})"


action_parser = some(
    pmap(lambda s: s[0],
         chain(
        options(ActionCall.parse, ActionOp.parse),
        semicolon_lit
    )))

# Filters


class ASRange(object):
    parser = options(
        chain(ASRef.parse, minus_lit, ASRef.parse),
        chain(num_lit, minus_lit, num_lit))

    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def __repr__(self):
        return f"ASRange({self.lower!r}, {self.upper!r})"
        pass

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2]), s


class ASSet(object):
    element_parser = options(
        ASRange.parse,
        num_lit,
        ASRef.parse)
    parser = chain(lb_lit, optional(caret_lit),
                   many(element_parser), rb_lit)

    def __init__(self, elements, complement=False):
        self.elements = elements
        self.complement = bool(complement)

    def __repr__(self):
        return f"ASSet({self.elements!r}, {self.complement!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[2], r[1]), s


as_regex_prim_op_parser = options(
    ast_lit,
    plus_lit,
    pmap(lambda s: s[1], chain(lbr_lit, num_lit, rbr_lit)),
    pmap(lambda s: (s[1], s[3]),
         chain(lbr_lit, num_lit, comma_lit, num_lit, rbr_lit)),
    pmap(lambda s: (s[1], None),
         chain(lbr_lit, num_lit, comma_lit, rbr_lit)))
as_regex_op_parser = options(
    as_regex_prim_op_parser,
    qm_lit,
    chain(tilde_lit, as_regex_prim_op_parser))

as_regex_parser = forward(lambda: as_regex_parser)
as_regex_expr_parser = chain(options(
    ASRef.parse,
    ASSetRef.parse,
    ASSet.parse,
    dot_lit,
    dollar_lit,
    caret_lit,
    chain(lpar_lit, as_regex_parser, rpar_lit)),
    many(as_regex_op_parser))
as_regex_parser = sep_by(
    many(as_regex_expr_parser),
    pipe_lit)

filter_rs_parser = chain(ObjectRef.parse, optional(PrefixRange.parse))

filter_parser = forward(lambda: filter_parser)
filter_expr_parser = options(
    chain(lpar_lit, filter_parser, rpar_lit),
    any_lit,
    peer_as_lit,
    ActionCall.parse,
    filter_rs_parser,
    PrefixSet.parse,
    chain(lt_lit, as_regex_parser, gt_lit))
filter_parser = sep_by(
    sep_by(chain(optional(not_lit), filter_expr_parser), and_lit),
    options(or_lit, lookahead(filter_parser)))


# Peering specification

as_expr_parser = forward(lambda: as_expr_parser)
as_expr_parser = sep_by(
    options(ASRef.parse,
            ASSetRef.parse,
            pmap(lambda s: s[1],
                 chain(lbr_lit, as_expr_parser, rbr_lit))),
    options(and_lit, or_lit, except_lit),
    True)

router_expr_parser = forward(lambda: router_expr_parser)
router_expr_parser = sep_by(
    options(ip_address_parser, RouterRef.parse,
            pmap(lambda s: s[1],
                 chain(lbr_lit, router_expr_parser, rbr_lit))),
    options(and_lit, or_lit, except_lit),
    True)


class PeeringSpec(object):
    parser = chain(as_expr_parser,
                   optional(router_expr_parser),
                   optional(pmap(lambda s: s[1],
                                 chain(at_lit, router_expr_parser))))

    def __init__(self, as_expression, router, at_router):
        self.as_expression = as_expression
        self.router = router
        self.at_router = at_router

    def __repr__(self):
        return f"PeeringSpec({self.as_expression!r}, {self.router!r}, {self.at_router!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        as_expression = r[0]
        router_expr1, router_expr2 = r[1], r[2]
        return cls(as_expression, r[1], r[2]), s


peering_parser = options(
    PeeringSpec.parse,
    PeeringSetRef.parse)

# Import

def _mk_factor_parser(from_lit, accept_lit):
    peerings_parser = pmap(
        lambda r: (r[1], r[2]),
        chain(from_lit, peering_parser,
              optional(pmap(
                  lambda r: r[1],
                  chain(action_lit, action_parser)))))
    parser = chain(
        peerings_parser,
        accept_lit,
        filter_parser,
        optional(semicolon_lit))
    return parser

class ImportFactor(object):
    parser = _mk_factor_parser(from_lit, accept_lit)

    def __init__(self, peering_actions, filter_):
        self.peering_actions = list(peering_actions)
        self.filter_ = filter_

    def __repr__(self):
        return f"{self.__class__.__name__}({self.peering_actions!r}, {self.filter_!r})"

    def __str__(self):
        s = ""
        for peering, action in self.peering_actions:
            s += f"from {self.peering} "
            if action is not None:
                s += f"action {self.action} "
        s += "accept "
        s += str(self.filter_)
        s += ";"
        return s

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2]), s


import_term_parser  = options(
    ImportFactor.parse,
    pmap(lambda s: s[1],
         chain(lbr_lit, many(ImportFactor.parse), rbr_lit)))

import_expression_parser = forward(lambda: import_expression_parser)
import_expression_parser = sep_by(
    import_term_parser,
    options(except_lit, refine_lit),
    inject=True)


def _mk_policy_parser(expr):
    return chain(optional(chain(protocol_lit, ObjectRef.parse)),
            optional(chain(into_lit, ObjectRef.parse)),
            expr,
            eof)

class ImportPolicy(object):
    parser = _mk_policy_parser(import_expression_parser)

    def __init__(self, expression, source_proto=None, sink_proto=None):
        self.expression = expression
        self.source_proto = source_proto
        self.sink_proto = sink_proto

    def __repr__(self):
        return f"{self.__class__.__name__}({self.expression!r}, {self.source_proto!r}, " + \
            f"{self.sink_proto!r})"

    def __str__(self):
        s = ""
        if self.source_proto:
            s += f"protocol {self.source_proto} "
        if self.sink_proto:
            s += f"into {self.sink_proto} "
        return s + str(self.expression)

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        proto = r[0]
        into = r[1]
        expr = r[2]
        if proto is not None:
            proto = proto[1]
        if into is not None:
            into = into[1]
        return cls(expr, proto, into), s


import_parser = ImportPolicy.parse

# Export

class ExportFactor(ImportFactor):
    parser = _mk_factor_parser(to_lit, announce_lit)

export_term_parser  = options(
    ExportFactor.parse,
    pmap(lambda s: s[1],
         chain(lbr_lit, many(ExportFactor.parse), rbr_lit)))

export_expression_parser = forward(lambda: export_expression_parser)
export_expression_parser = sep_by(
    export_term_parser,
    options(except_lit, refine_lit),
    inject=True)

class ExportPolicy(ImportPolicy):
    parser = _mk_policy_parser(export_expression_parser)

# Inject
condition_parser = sep_by(
    options(
        static_lit,
        chain(have_components_lit, PrefixSet.parse),
        chain(exclude_lit, PrefixSet.parse),
    ), options(and_lit, or_lit),
    inject=True)


class InjectPolicy(object):
    expression_parser = chain(
        many(chain(at_lit, router_expr_parser)),
        optional(chain(action_lit, action_parser)),
        optional(chain(upon_lit, condition_parser)))
    parser = chain(expression_parser, eof)

    def __init__(self, routers, action, condition):
        self.routers = list(routers)
        self.action = action
        self.condition = condition

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        r = r[0]
        routers = r[0]
        action = r[1]
        upon = r[2]
        if action is not None:
            action = action[1]
        if upon is not None:
            upon = upon[1]
        return cls(routers, action, upon)


# Multiprotocol
afi_parser = chain(afi_lit, afi_value_lit)


class AFI(object):
    parser = chain(afi_lit, afi_value_lit)

    def __init__(self, afi):
        self.afi = afi

    def __repr__(self):
        return f"AFI({self.afi!r})"

    def __str__(self):
        return f"afi {self.afi}"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[1]), s


mp_import_parser = chain(AFI.parse, ImportPolicy.parse)
mp_export_parser = chain(AFI.parse, ExportPolicy.parse)
