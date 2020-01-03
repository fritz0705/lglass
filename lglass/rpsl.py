from __future__ import annotations
from typing import *

from unicodedata import category
from functools import wraps


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
any_lit = token(const("ANY"))
protocol_lit = token(const("protocol"))
into_lit = token(const("into"))
caret_lit = token(const("^"))
minus_lit = token(const("-"))
plus_lit = token(const("+"))
slash_lit = token(const("/"))
num_lit = pmap(int, pmap("".join, token(some(satisfy(is_number)))))


def colon_num_lit(s):
    h, s = some(satisfy(is_number))(s)
    c, s = const(":")(s)
    l, s = some(satisfy(is_number))(s)
    _, s = spaces(s)
    h, l = int("".join(h)), int("".join(l))
    return (h << 16) | l, s


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
except_lit = token(const("EXCEPT"))
refine_lit = token(const("REFINE"))
peer_as_lit = token(const("PeerAS"))
and_lit = token(const("AND"))
or_lit = token(const("OR"))
not_lit = token(const("NOT"))
dollar_lit = token(const("$"))
upon_lit = token(const("upon"))
static_lit = token(const("STATIC"))
at_lit = token(const("at"))
have_components_lit = token(const("HAVE-COMPONENTS"))
exclude_lit = token(const("EXCLUDE"))
networks_lit = token(const("networks"))
atomic_lit = token(const("ATOMIC"))
inbound_lit = token(const("inbound"))
outbound_lit = token(const("outbound"))
mandatory_lit = token(const("MANDATORY"))
optional_lit = token(const("OPTIONAL"))


class SyntaxNode(object):
    def sub_nodes(self):
        ...


class ObjectRef(SyntaxNode):
    parser = token(chain(satisfy(is_letter), many(options(
        satisfy(is_letter),
        satisfy(is_number),
        one_of(":-_.")))))

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

    def sub_nodes(self):
        yield self.primary_key


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


class RouterSetRef(ObjectRef):
    parser = chain(const("RTRS-"), ObjectRef.parser)

    def __init__(self, primary_key, classes={"rtr-set"}):
        super().__init__(primary_key, classes)


class RouterRef(ObjectRef):
    component_parser = chain(satisfy(is_letter), many(options(
        satisfy(is_letter),
        satisfy(is_number),
        one_of("-"))))
    parser = token(chain(
        component_parser,
        const("."),
        optional(sep_by(component_parser, const("."), True))))

    def __init__(self, primary_key, classes={"inet-rtr"}):
        super().__init__(primary_key, classes)


class RouteSetRef(ObjectRef):
    parser = chain(const("RS-"), ObjectRef.parser)

    def __init__(self, primary_key, classes={"route-set"}):
        super().__init__(primary_key, classes)


class IPv4Address(SyntaxNode):
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

    def sub_nodes(self):
        yield self.address


hexdigit_parser = one_of("abcdefABCDEF0123456789")


class IPv6Address(SyntaxNode):
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

    def sub_nodes(self):
        yield self.address


ip_address_parser = options(IPv4Address.parse, IPv6Address.parse)


class PrefixRange(SyntaxNode):
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

    def __str__(self):
        return flatten(self.range)

    def sub_nodes(self):
        yield from ()


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

    def __str__(self):
        s = ", ".join(f"{prefix}/{length}{range_ if range_ else ''}"
                      for prefix, length, range_ in self.prefixes)
        return "{ " + s + " }" + (str(self.range_) if self.range_ else "")

    def sub_nodes(self):
        for prefix in self.prefixes:
            yield from prefix
        yield self.range_


# Values
value_parser = forward(lambda: value_parser)


class ValueList(SyntaxNode):
    parser = chain(lbr_lit,
                   optional(sep_by(value_parser, comma_lit)),
                   rbr_lit)

    def __init__(self, values=list()):
        self.values = list(values)

    def __repr__(self):
        return f"ValueList({self.values!r})"

    def __str__(self):
        return "{ " + ", ".join(map(str, self.values)) + " }"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        r = r[1]
        if r is None:
            r = ()
        return cls(r), s

    def sub_nodes(self):
        yield from self.values


# TODO Implement A:B integer representation
value_parser = options(ValueList.parse,
                       colon_num_lit,
                       num_lit,
                       ObjectRef.parse)

# Actions


class ActionCall(SyntaxNode):
    args_parser = sep_by(value_parser, comma_lit)
    parser = chain(sep_by(ObjectRef.parse, dot_lit), lpar_lit,
                   optional(args_parser), rpar_lit)

    def __init__(self, func, args):
        self.func = func
        self.args = args

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2] or ()), s

    def __repr__(self):
        return f"ActionCall({self.func!r}, {self.args!r})"

    def __str__(self):
        return ".".join(map(str, self.func)) + "(" + ", ".join(map(str, self.args)) + ")"

    def sub_nodes(self):
        yield from self.func
        yield from self.args


class ActionOp(SyntaxNode):
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

    def __str__(self):
        return f"{self.attr} {self.operator} {self.value}"

    def sub_nodes(self):
        yield self.attr
        yield self.operator
        yield self.value


action_parser = options(ActionCall.parse, ActionOp.parse)
actions_parser = some(
    pmap(lambda s: s[0],
         chain(
        action_parser,
        semicolon_lit
    )))

# Filters


class ASRange(SyntaxNode):
    parser = options(
        chain(ASRef.parse, minus_lit, ASRef.parse),
        chain(num_lit, minus_lit, num_lit))

    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def __repr__(self):
        return f"ASRange({self.lower!r}, {self.upper!r})"

    def __str__(self):
        return f"{self.lower}-{self.upper}"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2]), s

    def sub_nodes(self):
        yield self.lower
        yield self.upper


class ASSet(SyntaxNode):
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

    def __self__(self):
        return "[" + "^" * self.complement + " ".join(map(str, self.elements))

    def sub_nodes(self):
        if self.complement:
            yield '^'
        yield from self.elements


class ASRegexQuantifier(SyntaxNode):
    prim_parser = options(
        ast_lit,
        plus_lit,
        pmap(lambda s: s[1], chain(lbr_lit, num_lit, rbr_lit)),
        pmap(lambda s: (s[1], s[3]),
             chain(lbr_lit, num_lit, comma_lit, num_lit, rbr_lit)),
        pmap(lambda s: (s[1], None),
             chain(lbr_lit, num_lit, comma_lit, rbr_lit)))
    parser = options(
        prim_parser,
        qm_lit,
        chain(tilde_lit, prim_parser))

    def __init__(self, minimum, maximum, same=False):
        self.minimum = minimum
        self.maximum = maximum
        self.same = bool(same)

    def __repr__(self):
        return f"ASRegexQuantifier({self.minimum!r}, {self.maximum!r}, {self.same!r})"

    def __str__(self):
        s = ""
        if self.same:
            s = "~"
        if self.minimum == 0 and self.maximum == None:
            s += "*"
        elif self.minimum == 1 and self.maximum == None:
            s += "+"
        elif self.minimum == 0 and self.maximum == 1:
            s += "?"
        elif self.minimum == self.maximum:
            s += "{"
            s += f"{self.minimum}"
            s += "}"
        elif self.maximum is None:
            s += "{"
            s += f"{self.minimum}"
            s += "}"
        else:
            s += "{"
            s += f"{self.minimum},{self.maximum}"
            s += "}"
        return s

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        same = False
        if isinstance(r, list):
            same = True
            r = r[1]
        minimum, maximum = 0, None
        if isinstance(r, int):
            minimum, maximum = r, r
        elif r == '*':
            minimum, maximum = 0, None
        elif r == '+':
            minimum, maximum = 1, None
        elif r == '?':
            minimum, maximum = 0, 1
        elif isinstance(r, tuple):
            minimum, maximum = r
        return cls(minimum, maximum, same), s

    def sub_nodes(self):
        yield str(self)


as_regex_parser = forward(lambda: as_regex_parser)


class ASRegexExpr(SyntaxNode):
    parser = chain(options(
        ASRef.parse,
        ASSetRef.parse,
        ASSet.parse,
        dot_lit,
        dollar_lit,
        caret_lit,
        pmap(lambda s: s[1], chain(lpar_lit, as_regex_parser, rpar_lit))),
        many(ASRegexQuantifier.parse))

    def __init__(self, element, operators):
        self.element = element
        self.operators = list(operators)

    def __repr__(self):
        return f"ASRegexExpr({self.element!r}, {self.operators!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[1]), s

    def __str__(self):
        return str(self.element) + "".join(map(str, self.operators))

    def sub_nodes(self):
        yield self.element
        yield from self.operators


class ASRegex(SyntaxNode):
    parser = some(ASRegexExpr.parse)

    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return f"ASRegex({self.children!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r), s

    def __str__(self):
        return " ".join(map(str, self.children))

    def sub_nodes(self):
        yield from self.children


class ASRegexAlt(SyntaxNode):
    parser = sep_by(ASRegex.parse, pipe_lit)

    def __init__(self, alternatives):
        self.alternatives = alternatives

    def __repr__(self):
        return f"ASRegexAlt({self.alternatives!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser
        if len(r) == 1:
            return r[0], s
        return cls(r), s

    def __str__(self):
        return " | ".join(map(str, self.alternatives))

    def sub_nodes(self):
        yield from self.alternatives


as_regex_parser = ASRegex.parse


class FilterRS(SyntaxNode):
    parser = chain(options(
        RouteSetRef.parse,
        ASSetRef.parse,
        ASRef.parse), optional(PrefixRange.parse))

    def __init__(self, obj, range_=None):
        self.obj = obj
        self.range_ = range_

    def __repr__(self):
        return f"FilterRS({self.obj!r}, {self.range_!r})"

    def __str__(self):
        return f"{self.obj}{self.range_ if self.range_ else ''}"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[1]), s

    def sub_nodes(self):
        yield self.obj
        yield self.range_


filter_parser = forward(lambda: filter_parser)


class Filter(SyntaxNode):
    pass


class FilterExpr(Filter):
    parser = options(
        pmap(lambda r: r[1], chain(lpar_lit, filter_parser, rpar_lit)),
        any_lit,
        peer_as_lit,
        ActionCall.parse,
        FilterRS.parse,
        PrefixSet.parse,
        pmap(lambda r: r[1], chain(lt_lit, as_regex_parser, gt_lit)))

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"FilterExpr({self.value!r})"

    def __str__(self):
        if isinstance(self.value, ASRegex):
            return "<" + str(self.value) + ">"
        elif isinstance(self.value, Filter):
            return "(" + str(self.value) + ")"
        return str(self.value)

    @property
    def is_any(self):
        return self.value == "any"

    @property
    def is_peer_as(self):
        return self.value == "peeras"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r), s

    def sub_nodes(self):
        yield self.value


class FilterNot(Filter):
    parser = chain(optional(not_lit), FilterExpr.parse)

    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"FilterNot({self.expr!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        if r[0] is None:
            return r[1], s
        return cls(r[1]), s

    def sub_nodes(self):
        yield self.expr

    def __str__(self):
        return f"NOT {self.expr}"


class FilterAnd(Filter):
    parser = sep_by(
        FilterNot.parse,
        and_lit)

    def __init__(self, exprs):
        self.exprs = exprs

    def __repr__(self):
        return f"FilterAnd({self.exprs!r})"

    def __str__(self):
        return " AND ".join(map(str, self.exprs))

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        if len(r) == 1:
            return r[0], s
        return cls(r), s

    def sub_nodes(self):
        yield from self.exprs


class FilterOr(Filter):
    parser = forward(lambda: FilterOr.parser)
    parser = sep_by(
        FilterAnd.parse,
        options(or_lit, lookahead(parser)))

    def __init__(self, exprs):
        self.exprs = exprs

    def __repr__(self):
        return f"FilterOr({self.exprs!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        if len(r) == 1:
            return r[0], s
        return cls(r), s

    def sub_nodes(self):
        yield from self.exprs

    def __str__(self):
        return f" OR ".join(map(str, self.exprs))


filter_parser = FilterOr.parse

# Peering specification


class ASExpr(SyntaxNode):
    parser = forward(lambda: ASExpr.parse)
    parser = sep_by(
        options(ASRef.parse,
                ASSetRef.parse,
                pmap(lambda s: s[1],
                     chain(lbr_lit, parser, rbr_lit))),
        options(and_lit, or_lit, except_lit),
        True)

    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return f"ASExpr({self.children!r})"

    def __str__(self):
        return " ".join(map(str, self.children))

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r), s

    def sub_nodes(self):
        yield from self.children


class RouterExpr(SyntaxNode):
    parser = forward(lambda: RouterExpr.parse)
    parser = sep_by(
        options(ip_address_parser,
                RouterSetRef.parse,
                RouterRef.parse,
                pmap(lambda s: s[1],
                     chain(lbr_lit, parser, rbr_lit))),
        options(and_lit, or_lit, except_lit),
        True)

    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return f"RouterExpr({self.children!r})"

    def __str__(self):
        return " ".join(map(str, self.children))

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r), s

    def sub_nodes(self):
        yield from self.children


class PeeringSpec(SyntaxNode):
    parser = chain(ASExpr.parse,
                   optional(RouterExpr.parse),
                   optional(pmap(lambda s: s[1],
                                 chain(at_lit, RouterExpr.parse))))

    def __init__(self, as_expression, router, at_router):
        self.as_expression = as_expression
        self.router = router
        self.at_router = at_router

    def __repr__(self):
        return f"PeeringSpec({self.as_expression!r}, {self.router!r}, {self.at_router!r})"

    def __str__(self):
        s = f"{self.as_expression}"
        if self.router:
            s += f" {self.router}"
        if self.at_router:
            s += f" at {self.at_router}"
        return s

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        as_expression = r[0]
        router_expr1, router_expr2 = r[1], r[2]
        return cls(as_expression, r[1], r[2]), s

    def sub_nodes(self):
        yield self.as_expression
        yield self.router
        yield self.at_router


peering_parser = options(
    PeeringSpec.parse,
    PeeringSetRef.parse)

# Import


class ImportFactor(SyntaxNode):
    peerings_parser = pmap(
        lambda r: (r[1], r[2]),
        chain(from_lit, peering_parser,
              optional(pmap(
                  lambda r: r[1],
                  chain(action_lit, actions_parser)))))
    parser = chain(
        many(peerings_parser),
        accept_lit,
        filter_parser,
        optional(semicolon_lit))

    def __init__(self, peering_actions, filter_):
        self.peering_actions = list(peering_actions)
        self.filter_ = filter_

    def __repr__(self):
        return f"{self.__class__.__name__}({self.peering_actions!r}, {self.filter_!r})"

    def __str__(self):
        s = ""
        for peering, actions in self.peering_actions:
            s += f"from {peering} "
            if actions is not None:
                s += "action "
                for action in actions:
                    s += str(action) + "; "
        s += "accept "
        s += str(self.filter_)
        s += ";"
        return s

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2]), s

    def sub_nodes(self):
        for peering, actions in self.peering_actions:
            yield peering
            if actions:
                yield from actions
        yield self.filter_


class ImportFactorList(SyntaxNode):
    parser = chain(lbr_lit, many(ImportFactor.parse), rbr_lit)

    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return f"ImportTermList({self.children!r})"

    def __str__(self):
        return "{ " + " ".join(map(str, self.children)) + " }"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[1]), s

    def sub_nodes(self):
        yield from self.children


import_term_parser = options(
    ImportFactor.parse,
    ImportFactorList.parse)

import_expr_parser = forward(lambda: ImportExpr.parse)


class ImportExpr(SyntaxNode):
    parser = options(
        forward(lambda: ImportExceptExpr.parse),
        forward(lambda: ImportRefineExpr.parse),
        import_term_parser)

    @classmethod
    def parse(cls, s):
        return cls.parser(s)


class ImportExceptExpr(ImportExpr):
    parser = chain(import_term_parser, except_lit, import_expr_parser)

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return str(self.left) + " EXCEPT " + str(self.right)

    def __repr__(self):
        return f"ImportExceptExpr({self.left!r}, {self.right!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2]), s

    def sub_nodes(self):
        yield self.left
        yield self.right


class ImportRefineExpr(ImportExpr):
    parser = chain(import_term_parser, refine_lit, import_expr_parser)

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return str(self.left) + " REFINE " + str(self.right)

    def __repr__(self):
        return f"ImportRefineExpr({self.left!r}, {self.right!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2]), s

    def sub_nodes(self):
        yield self.left
        yield self.right


import_expr_parser = ImportExpr.parse


class ImportPolicy(SyntaxNode):
    parser = chain(optional(chain(protocol_lit, ObjectRef.parse)),
                   optional(chain(into_lit, ObjectRef.parse)),
                   import_expr_parser,
                   eof)

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

    def sub_nodes(self):
        yield self.expression
        yield self.source_proto
        yield self.sink_proto


import_parser = ImportPolicy.parse

# Export


class ExportFactor(SyntaxNode):
    peerings_parser = pmap(
        lambda r: (r[1], r[2]),
        chain(to_lit, peering_parser,
              optional(pmap(
                  lambda r: r[1],
                  chain(action_lit, actions_parser)))))
    parser = chain(
        many(peerings_parser),
        announce_lit,
        filter_parser,
        optional(semicolon_lit))

    def __init__(self, peering_actions, filter_):
        self.peering_actions = list(peering_actions)
        self.filter_ = filter_

    def __repr__(self):
        return f"{self.__class__.__name__}({self.peering_actions!r}, {self.filter_!r})"

    def __str__(self):
        s = ""
        for peering, actions in self.peering_actions:
            s += f"from {peering} "
            if actions is not None:
                s += "action "
                for action in actions:
                    s += str(action) + "; "
        s += "announce "
        s += str(self.filter_)
        s += ";"
        return s

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2]), s

    def sub_nodes(self):
        for peering, actions in self.peering_actions:
            yield peering
            if actions:
                yield from actions
        yield self.filter_


class ExportFactorList(SyntaxNode):
    parser = chain(lbr_lit, many(ExportFactor.parse), rbr_lit)

    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return f"ExportTermList({self.children!r})"

    def __str__(self):
        return "{ " + " ".join(map(str, self.children)) + " }"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[1]), s

    def sub_nodes(self):
        yield from self.children


export_term_parser = options(
    ExportFactor.parse,
    ExportFactorList.parse)

export_expr_parser = forward(lambda: ExportExpr.parse)


class ExportExpr(SyntaxNode):
    parser = options(
        forward(lambda: ExportExceptExpr.parse),
        forward(lambda: ExportRefineExpr.parse),
        export_term_parser)

    @classmethod
    def parse(cls, s):
        return cls.parser(s)


class ExportExceptExpr(ExportExpr):
    parser = chain(export_term_parser, except_lit, export_expr_parser)

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return str(self.left) + " EXCEPT " + str(self.right)

    def __repr__(self):
        return f"ExportExceptExpr({self.left!r}, {self.right!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2]), s

    def sub_nodes(self):
        yield self.left
        yield self.right


class ExportRefineExpr(ExportExpr):
    parser = chain(export_term_parser, refine_lit, export_expr_parser)

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __str__(self):
        return str(self.left) + " REFINE " + str(self.right)

    def __repr__(self):
        return f"ExportRefineExpr({self.left!r}, {self.right!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[2]), s

    def sub_nodes(self):
        yield self.left
        yield self.right


export_expr_parser = ExportExpr.parse


class ExportPolicy(SyntaxNode):
    parser = chain(optional(chain(protocol_lit, ObjectRef.parse)),
                   optional(chain(into_lit, ObjectRef.parse)),
                   export_expr_parser,
                   eof)

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

    def sub_nodes(self):
        yield self.expression
        yield self.source_proto
        yield self.sink_proto


export_parser = ExportPolicy.parse

# Default


class DefaultPolicy(SyntaxNode):
    parser = chain(to_lit, peering_parser,
                   optional(chain(action_lit, actions_parser)),
                   optional(chain(networks_lit, filter_parser)),
                   eof)

    def __init__(self, peering, action, filter_):
        self.peering = peering
        self.action = action
        self.filter = filter_

    def __repr__(self):
        return f"DefaultPolicy({self.peering!r}, {self.action!r}, {self.filter!r})"

    def __str__(self):
        s = "to " + str(self.peering)
        if self.action:
            s += " action " + str(self.action)
        if self.filter:
            s += " networks " + str(self.filter)
        return s

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        action = r[2][1] if r[2] else None
        filter_ = r[3][1] if r[3] else None
        return cls(r[1], action, filter_), s

    def sub_nodes(self):
        yield self.peering
        yield self.action
        yield self.filter


# Inject
class InjectCondition(SyntaxNode):
    pass


class InjectHaveComponents(InjectCondition):
    parser = chain(have_components_lit, PrefixSet.parse)

    def __init__(self, prefixes):
        self.prefixes = prefixes

    def __repr__(self):
        return f"InjectHaveComponents({self.prefixes!r})"

    def __str__(self):
        return f"HAVE-COMPONENTS {self.prefixes}"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[1]), s


class InjectExclude(InjectCondition):
    parser = chain(exclude_lit, PrefixSet.parse)

    def __init__(self, prefixes):
        self.prefixes = prefixes

    def __repr__(self):
        return f"InjectExclude({self.prefixes!r})"

    def __str__(self):
        return f"EXCLUDE {self.prefixes}"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[1]), s


class InjectStatic(InjectCondition):
    parser = static_lit

    def __repr__(self):
        return "InjectStatic()"

    def __str__(self):
        return "STATIC"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(), s


class InjectAnd(InjectCondition):
    parser = sep_by(options(
        InjectStatic.parse,
        InjectHaveComponents.parse,
        InjectExclude.parse),
        and_lit)

    def __init__(self, exprs):
        self.exprs = exprs

    def __str__(self):
        return " AND ".join(map(str, self.exprs))

    def __repr__(self):
        return f"InjectAnd({self.exprs!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        if len(r) == 1:
            return r[0], s
        return cls(r), s


class InjectOr(InjectCondition):
    parser = sep_by(InjectAnd.parser, or_lit)

    def __init__(self, exprs):
        self.exprs = exprs

    def __str__(self):
        return " OR ".join(map(str, self.exprs))

    def __repr__(self):
        return f"InjectOr({self.exprs!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        if len(r) == 1:
            return r[0], s
        return cls(r), s


inject_condition_parser = InjectOr.parse


class InjectPolicy(SyntaxNode):
    expression_parser = chain(
        many(chain(at_lit, RouterExpr.parse)),
        optional(chain(action_lit, actions_parser)),
        optional(chain(upon_lit, inject_condition_parser)))
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

    def sub_nodes(self):
        yield from self.routers
        yield self.action
        yield self.condition


# Multiprotocol
afi_parser = chain(afi_lit, afi_value_lit)


class AFI(SyntaxNode):
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

    def sub_nodes(self):
        yield self.afi


class MPImportPolicy(ImportPolicy):
    parser = chain(AFI.parse, ImportPolicy.parse)

    def __init__(self, afi, expression, source_proto=None, sink_proto=None):
        super().__init__(expression, source_proto, sink_proto)
        self.afi = afi

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[1].expression, r[1].source_proto, r[1].sink_proto), s

    def __repr__(self):
        return f"MPImportPolicy({self.afi!r}, {self.expression!r}, " + \
            f"{self.source_proto!r}, {self.sink_proto!r})"

    def __str__(self):
        return f"{self.afi} {super().__str__()}"

    def sub_nodes(self):
        yield self.afi
        yield from super().sub_nodes()


class MPExportPolicy(ExportPolicy):
    parser = chain(AFI.parse, ExportPolicy.parse)

    def __init__(self, afi, expression, source_proto=None, sink_proto=None):
        super().__init__(expression, source_proto, sink_proto)
        self.afi = afi

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[1].expression, r[1].source_proto, r[1].sink_proto), s

    def __repr__(self):
        return f"MPExportPolicy({self.afi!r}, {self.expression!r}, " + \
            f"{self.source_proto!r}, {self.sink_proto!r})"

    def __str__(self):
        return f"{self.afi} {super().__str__()}"

    def sub_nodes(self):
        yield self.afi
        yield from super().sub_nodes()


import_parser = ImportPolicy.parse
export_parser = ExportPolicy.parse
inject_parser = InjectPolicy.parse
default_parser = DefaultPolicy.parse

mp_import_parser = MPImportPolicy.parse
mp_export_parser = MPExportPolicy.parse


def extract_ast(node):
    sub_nodes = []
    for sub_node in node.sub_nodes():
        if isinstance(sub_node, SyntaxNode):
            sub_nodes.append(extract_ast(sub_node))
        else:
            sub_nodes.append(sub_node)
    return (str(node), sub_nodes)


if __name__ == "__main__":
    import argparse
    import sys
    import pprint

    argparser = argparse.ArgumentParser()
    argparser.add_argument("type", choices=("import", "export", "mp-import",
                                            "mp-export", "filter", "inject",
                                            "prefix-set", "as-regex",
                                            "peering", "router", "default"))
    argparser.add_argument("-o", "--output", choices=("str", "repr", "ast"),
                           default="str")

    args = argparser.parse_args()
    r = sys.stdin.read()
    parsers = {
        "import": import_parser,
        "export": export_parser,
        "mp-import": mp_import_parser,
        "mp-export": mp_export_parser,
        "filter": filter_parser,
        "inject": inject_parser,
        "prefix-set": PrefixSet.parse,
        "as-regex": as_regex_parser,
        "peering": PeeringSpec.parse,
        "router": RouterExpr.parse,
        "default": default_parser,
    }

    r, s = parsers[args.type](r)

    if args.output == "str":
        print(r)
    elif args.output == "repr":
        print(repr(r))
    elif args.output == "ast":
        pprint.pprint(extract_ast(r))
