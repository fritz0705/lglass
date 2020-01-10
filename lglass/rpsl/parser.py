from __future__ import annotations
from typing import *

from unicodedata import category
from functools import wraps

from abc import *

from .pc import *


def failure(s: str) -> Tuple[T, str]:
    raise ParseException(s)


spaces = Many(space)


def flatten(l: Union[str, int, List[Any]]) -> str:
    if isinstance(l, list):
        return "".join(flatten(e) for e in l)
    elif l is None:
        return ""
    return str(l)


# Tokens
from_lit = Token(StrConst("from"))
action_lit = Token(StrConst("action"))
accept_lit = Token(StrConst("accept"))
announce_lit = Token(StrConst("announce"))
to_lit = Token(StrConst("to"))
op_lit = Token(Options(Const("<<="),
                       Const(">>="),
                       Const("+="),
                       Const("-="),
                       Const("*="),
                       Const("/="),
                       Const(".="),
                       Const("!="),
                       Const("<="),
                       Const(">="),
                       Const("=="),
                       Const("="),
                       Const("<"),
                       Const(">")))
hex_lit = PMap("".join, Token(Some(OneOf("abcdefABCDEF0123456789"))))
any_lit = Token(StrConst("ANY"))
protocol_lit = Token(StrConst("protocol"))
into_lit = Token(StrConst("into"))
caret_lit = Token(Const("^"))
minus_lit = Token(Const("-"))
plus_lit = Token(Const("+"))
slash_lit = Token(Const("/"))
num_lit = PMap(lambda r: int("".join(r)), Token)
num_lit = PMap(int, PMap("".join, Token(Some(numeric))))


@Parser
def colon_num_lit(s):
    h, s = Some(numeric)(s)
    c, s = Const(":")(s)
    l, s = Some(numeric)(s)
    _, s = spaces(s)
    h, l = int("".join(h)), int("".join(l))
    return (h << 16) | l, s


comma_lit = Token(Const(","))
semicolon_lit = Token(Const(";"))
dot_lit = Token(Const("."))
colon_lit = Token(Const(':'))
afi_lit = Token(StrConst("afi"))
lbr_lit = Token(Const('{'))
rbr_lit = Token(Const('}'))
lb_lit = Token(Const("["))
rb_lit = Token(Const("]"))
lt_lit = Token(Const("<"))
gt_lit = Token(Const(">"))
pipe_lit = Token(Const("|"))
lpar_lit = Token(Const("("))
rpar_lit = Token(Const(")"))
qm_lit = Token(Const("$"))
ast_lit = Token(Const("*"))
plus_lit = Token(Const("+"))
qm_lit = Token(Const("?"))
tilde_lit = Token(Const("~"))
afi_value_lit = Token(Options(StrConst("ipv4.unicast"),
                              StrConst("ipv4.multicast"),
                              StrConst("ipv4"),
                              StrConst("ipv6.unicast"),
                              StrConst("ipv6.multicast"),
                              StrConst("ipv6"),
                              StrConst("any.unicast"),
                              StrConst("any.multicast"),
                              StrConst("any")))
except_lit = Token(StrConst("EXCEPT"))
refine_lit = Token(StrConst("REFINE"))
peer_as_lit = Token(StrConst("PeerAS"))
and_lit = Token(StrConst("AND"))
or_lit = Token(StrConst("OR"))
not_lit = Token(StrConst("NOT"))
dollar_lit = Token(Const("$"))
upon_lit = Token(StrConst("upon"))
static_lit = Token(StrConst("STATIC"))
at_lit = Token(StrConst("at"))
have_components_lit = Token(StrConst("HAVE-COMPONENTS"))
exclude_lit = Token(StrConst("EXCLUDE"))
networks_lit = Token(StrConst("networks"))
atomic_lit = Token(StrConst("ATOMIC"))
inbound_lit = Token(StrConst("inbound"))
outbound_lit = Token(StrConst("outbound"))
mandatory_lit = Token(StrConst("MANDATORY"))
optional_lit = Token(StrConst("OPTIONAL"))


class SyntaxNode(ABC):
    @abstractmethod
    def sub_nodes(self):
        ...

    def map(self, f):
        yield from (sub_node.map(f) for sub_node in self.sub_nodes())


class ObjectRef(SyntaxNode):
    parser = Token(Chain(alpha, Many(Options(
        alpha,
        numeric,
        OneOf("-_.")))))

    def __init__(self, primary_key, classes=None):
        self.primary_key = primary_key
        if classes is not None:
            classes = frozenset(classes)
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

    def __eq__(self, other):
        if not isinstance(other, ObjectRef):
            return NotImplemented
        return self.primary_key == other.primary_key and \
            self.classes == other.classes

    def __hash__(self):
        return hash((self.primary_key, self.classes))

    def resolve(self, database):
        results = iter(database.lookup(classes=self.classes,
                                       keys=(self.primary_key,)))
        for result in results:
            try:
                next(results)
            except StopIteration:
                return database.fetch(*result)
            return None
        return None


class MntnerRef(ObjectRef):
    def __init__(self, primary_key, classes={"mntner"}):
        super().__init__(primary_key, classes)


class ASRef(ObjectRef):
    parser = Chain(StrConst("AS"), num_lit)

    def __init__(self, primary_key, classes={"aut-num"}):
        super().__init__(primary_key, classes)

    def __int__(self):
        return int(self.primary_key[2:])


def hier_set_name_parser(set_name_parser):
    def _parser(seq):
        seq_orig = seq
        valid = False
        res = None
        try:
            res, seq = set_name_parser(seq)
        except ParseException:
            res, seq = ASRef.parser(seq)
        else:
            valid = True
        ret = [res]
        while True:
            try:
                _, seq_new = colon_lit(seq)
            except ParseException:
                break
            else:
                ret.append(":")
                seq = seq_new
            try:
                res, seq = set_name_parser(seq)
            except ParseException:
                res, seq = ASRef.parse(seq)
                ret.append(res)
            else:
                ret.append(res)
                valid = True
        if not valid:
            raise ParseException(seq_orig,
                                 f'<hier_set_name_parser {set_name_parser!r}>',
                                 f'hier_set_name_parser({set_name_parser!r})')
        return ret, seq
    return Parser(_parser, f"hier_set_name({set_name_parser!r})")


class ASSetRef(ObjectRef):
    parser = hier_set_name_parser(Chain(StrConst("AS-"), ObjectRef.parser))

    def __init__(self, primary_key, classes={"as-set"}):
        super().__init__(primary_key, classes)


class PeeringSetRef(ObjectRef):
    parser = hier_set_name_parser(Chain(StrConst("PRNG-"), ObjectRef.parser))

    def __init__(self, primary_key, classes={"peering-set"}):
        super().__init__(primary_key, classes)


class RouterSetRef(ObjectRef):
    parser = hier_set_name_parser(Chain(StrConst("RTRS-"), ObjectRef.parser))

    def __init__(self, primary_key, classes={"rtr-set"}):
        super().__init__(primary_key, classes)


class RouterRef(ObjectRef):
    component_parser = Chain(alpha, Many(Options(
        alpha,
        numeric,
        Const("-"))))
    parser = Token(Chain(
        component_parser,
        Const("."),
        optional(SepBy(component_parser, Const("."), True))))

    def __init__(self, primary_key, classes={"inet-rtr"}):
        super().__init__(primary_key, classes)


class RouteSetRef(ObjectRef):
    parser = hier_set_name_parser(Chain(StrConst("RS-"), ObjectRef.parser))

    def __init__(self, primary_key, classes={"route-set"}):
        super().__init__(primary_key, classes)


class IPv4Address(SyntaxNode):
    octet_parser = Options(
        Chain(Const("25"), OneOf("012345")),
        Chain(Const("1"), numeric, numeric),
        Chain(numeric, numeric),
        numeric)
    parser = Token(Chain(octet_parser, Const("."), octet_parser, Const("."),
                         octet_parser, Const("."), octet_parser))

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

    def __eq__(self, other):
        return self.address == other.address

    def __hash__(self):
        return hash(self.address)


def generate_ipv6_parser(hextet_parser, ls32_parser):
    # Colon Parser
    cp = Const(":")
    # Double Colon Parser
    dcp = Const("::")
    # Hextet Colon Parser
    hcp = Chain(hextet_parser, cp, FailIf(Lookahead(cp)))
    full_parser = Chain(Range(hcp, {6}), ls32_parser)
    shortened_parsers = []
    # Generate parsers for '::'-style addresses
    for hextets_right in (7, 6, 5, 4, 3, 2, 1, 0):
        hextets_left = 7 - hextets_right
        left_parser, right_parsers = None, []
        if hextets_left > 1:
            left_parser = Chain(Range(hcp, range(hextets_left)), hextet_parser)
            left_parser = optional(left_parser)
        elif hextets_left > 0:
            left_parser = optional(hextet_parser)
        if hextets_right > 3:
            right_parsers = [Range(hcp, {hextets_right - 2}),
                             ls32_parser]
        elif hextets_right == 3:
            right_parsers = [hcp, ls32_parser]
        elif hextets_right == 2:
            right_parsers = [ls32_parser]
        elif hextets_right == 1:
            right_parsers = [hextet_parser]
        parsers = ([left_parser] if left_parser else []) + \
            [dcp] + right_parsers
        shortened_parsers.append(Chain(*parsers))
    parsers = [full_parser] + shortened_parsers
    return Options(*parsers)


class IPv6Address(SyntaxNode):
    hexdigit_parser = OneOf("abcdefABCDEF0123456789")
    hextet_parser = Range(hexdigit_parser, {1, 2, 3, 4})
    ls32_parser = Options(
        Chain(hextet_parser, Const(":"), hextet_parser),
        IPv4Address.parser.parser)
    parser = generate_ipv6_parser(hextet_parser,
                                  ls32_parser)
    parser = Token(parser)

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

    def __eq__(self, other):
        return self.address == other.address

    def __hash__(self):
        return hash(self.address)


ip_address_parser = Options(IPv4Address.parse, IPv6Address.parse)


class PrefixRange(SyntaxNode):
    parser = Chain(caret_lit,
                   Options(minus_lit,
                           plus_lit,
                           Chain(num_lit, minus_lit, num_lit),
                           num_lit))

    def __init__(self, range_):
        if isinstance(range_, list):
            range_ = tuple(range_)
        self.range = tuple(range_)

    @classmethod
    def parse(cls, s):
        p, s = cls.parser(s)
        return cls(p[1]), s

    def __repr__(self):
        return f"PrefixRange({self.range!r})"

    def __str__(self):
        return flatten(self.range)

    def sub_nodes(self):
        yield from ()

    def __eq__(self, other):
        return self.range == other.range

    def __hash__(self):
        return hash(self.range)


class AddressPrefixRange(SyntaxNode):
    range_parser = Chain(caret_lit,
                         Options(minus_lit,
                                 plus_lit,
                                 Chain(num_lit, minus_lit, num_lit),
                                 num_lit))
    parser = Chain(ip_address_parser,
                   slash_lit,
                   num_lit,
                   optional(range_parser))

    def __init__(self, address, prefixlen, lower, upper):
        self.address = address
        self.prefixlen = prefixlen
        self.lower = lower
        self.upper = upper

    @classmethod
    def parse(cls, s):
        parsed = cls.parser(s)
        lower, upper = parsed[2]
        if (range_:= parsed[3]) is not None:
            range_ = range_[1]
            if range_ == '-':
                lower, upper = parsed[2] + 1, None
            elif range_ == '+':
                lower, upper = parsed[2], None
            elif isinstance(range_, int):
                lower, upper = range_, range_
            else:
                lower, upper = range_[0], range_[2]
        return cls(parsed[0], parsed[2], lower, upper)

    def __repr__(self):
        return f"AddressPrefixRange({self.address!r}, {self.prefixlen!r}, \
                {self.lower!r}, {self.upper!r})"

    def __str__(self):
        s = str(self.address) + "/" + str(self.prefixlen)
        return s

    def __hash__(self):
        return hash(self.address, self.prefixlen, self.lower, self.upper)

    def __eq__(self, other):
        return self.address == other.address and \
            self.prefixlen == other.prefixlen and \
            self.lower == other.lower and \
            self.upper == other.upper

    def sub_nodes(self):
        yield self.address


class PrefixSet(object):
    prefix_parser = Chain(ip_address_parser,
                          slash_lit,
                          num_lit,
                          optional(PrefixRange.parse))
    parser = Chain(lbr_lit,
                   optional(SepBy(AddressPrefixRange.parser, comma_lit)),
                   rbr_lit,
                   optional(PrefixRange.parse))

    def __init__(self, prefixes=set(), range_=None):
        self.prefixes = set(prefixes)
        self.range_ = range_

    @classmethod
    def parse(cls, s):
        parsed, s = cls.parser(s)
        prefixes = parsed[1] or ()
        global_range = parsed[3]
        return cls(prefixes, global_range), s

    def __repr__(self):
        return f"PrefixSet({self.prefixes!r}, {self.range_!r})"

    def __str__(self):
        s = ", ".join(str(prefix) for prefix in self.prefixes)
        return "{ " + s + " }" + (str(self.range_) if self.range_ else "")

    def sub_nodes(self):
        yield from self.prefixes
        yield self.range_

    def __eq__(self, other):
        return self.prefixes == other.prefixes and self.range_ == other.range_


# Values
value_parser = Forward(lambda: value_parser)


class ValueList(SyntaxNode):
    parser = Chain(lbr_lit,
                   optional(SepBy(value_parser, comma_lit)),
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

    def __eq__(self, other):
        return self.values == other.values


value_parser = Options(ValueList.parse,
                       colon_num_lit,
                       num_lit,
                       ObjectRef.parse)

# Actions


class RPAttributeName(SyntaxNode):
    parser = ObjectRef.parser

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"RPAttributeName({self.name!r})"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(flatten(r)), s

    def __str__(self):
        return self.name

    def sub_nodes(self):
        yield self.name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


class ActionCall(SyntaxNode):
    args_parser = SepBy(value_parser, comma_lit)
    parser = Chain(SepBy(RPAttributeName.parse, dot_lit), lpar_lit,
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
    parser = Chain(RPAttributeName.parse, op_lit, value_parser)

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


action_parser = Options(ActionCall.parse, ActionOp.parse)
actions_parser = Some(
    PMap(lambda s: s[0],
         Chain(
        action_parser,
        semicolon_lit
    )))

# Filters


class ASRange(SyntaxNode):
    parser = Options(
        Chain(ASRef.parse, minus_lit, ASRef.parse),
        Chain(num_lit, minus_lit, num_lit))

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

    def __eq__(self, other):
        return self.lower == other.lower and self.upper == other.upper

    def __hash__(self):
        return hash((self.lower, self.upper))


class ASSet(SyntaxNode):
    element_parser = Options(
        ASRange.parse,
        num_lit,
        ASRef.parse)
    parser = Chain(lb_lit, optional(caret_lit),
                   Many(element_parser), rb_lit)

    def __init__(self, elements, complement=False):
        self.elements = set(elements)
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

    def __eq__(self):
        return self.elements == other.elements \
            and self.complement == other.complement


class ASRegexQuantifier(SyntaxNode):
    prim_parser = Options(
        ast_lit,
        plus_lit,
        PMap(lambda s: s[1], Chain(lbr_lit, num_lit, rbr_lit)),
        PMap(lambda s: (s[1], s[3]),
             Chain(lbr_lit, num_lit, comma_lit, num_lit, rbr_lit)),
        PMap(lambda s: (s[1], None),
             Chain(lbr_lit, num_lit, comma_lit, rbr_lit)))
    parser = Options(
        prim_parser,
        qm_lit,
        Chain(tilde_lit, prim_parser))

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
            s += str(self.minimum)
            s += "}"
        elif self.maximum is None:
            s += "{"
            s += str(self.minimum)
            s += "}"
        else:
            s += "{"
            s += str(self.minimum) + "," + str(self.maximum)
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

    def __eq__(self, other):
        return self.minimum == other.minimum and \
            self.maximum == other.maximum and \
            self.same == other.same

    def __hash__(self, other):
        return hash((self.minimum, self.maximum, self.same))


as_regex_parser = Forward(lambda: as_regex_parser)


class ASRegexExpr(SyntaxNode):
    parser = Chain(Options(
        ASRef.parse,
        ASSetRef.parse,
        ASSet.parse,
        dot_lit,
        dollar_lit,
        caret_lit,
        PMap(lambda s: s[1], Chain(lpar_lit, as_regex_parser, rpar_lit))),
        Many(ASRegexQuantifier.parse))

    def __init__(self, element, operators):
        self.element = element
        self.operators = tuple(operators)

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

    def __eq__(self, other):
        return self.element == other.element and \
            self.operators == other.operators

    def __hash__(self):
        return hash((self.element, self.operators))


class ASRegex(SyntaxNode):
    parser = Some(ASRegexExpr.parse)

    def __init__(self, children):
        self.children = tuple(children)

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

    def __eq__(self, other):
        return self.children == other.children

    def __hash__(self):
        return hash(self.children)


class ASRegexAlt(SyntaxNode):
    parser = SepBy(ASRegex.parse, pipe_lit)

    def __init__(self, alternatives):
        self.alternatives = tuple(alternatives)

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

    def __eq__(self, other):
        return self.alternatives == other.alternatives

    def __hash__(self):
        return hash(self.alternatives)


as_regex_parser = ASRegex.parse


class FilterRS(SyntaxNode):
    parser = Chain(Options(
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


filter_parser = Forward(lambda: filter_parser)


class Filter(SyntaxNode):
    pass


class FilterExpr(Filter):
    parser = Options(
        PMap(lambda r: r[1], Chain(lpar_lit, filter_parser, rpar_lit)),
        any_lit,
        peer_as_lit,
        ActionCall.parse,
        FilterRS.parse,
        PrefixSet.parse,
        PMap(lambda r: r[1], Chain(lt_lit, as_regex_parser, gt_lit)))

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

    def __eq__(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)


class FilterNot(Filter):
    parser = Chain(optional(not_lit), FilterExpr.parse)

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

    def __eq__(self, other):
        return self.expr == other.expr

    def __hash__(self):
        return hash(self.expr)


class FilterAnd(Filter):
    parser = SepBy(
        FilterNot.parse,
        and_lit)

    def __init__(self, exprs):
        self.exprs = tuple(exprs)

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

    def __eq__(self, other):
        return self.exprs == other.exprs

    def __hash__(self):
        return hash(self.exprs)


class FilterOr(Filter):
    parser = Forward(lambda: FilterOr.parser)
    parser = SepBy(
        FilterAnd.parse,
        Options(or_lit, Lookahead(parser)))

    def __init__(self, exprs):
        self.exprs = tuple(exprs)

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

    def __eq__(self, other):
        return self.exprs == other.exprs

    def __hash__(self):
        return hash(self.exprs)


filter_parser = FilterOr.parse

# Peering specification


class ASExpr(SyntaxNode):
    parser = Forward(lambda: ASExpr.parse)
    parser = SepBy(
        Options(ASRef.parse,
                ASSetRef.parse,
                PMap(lambda s: s[1],
                     Chain(lbr_lit, parser, rbr_lit))),
        Options(and_lit, or_lit, except_lit),
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
    parser = Forward(lambda: RouterExpr.parse)
    parser = SepBy(
        Options(ip_address_parser,
                RouterSetRef.parse,
                RouterRef.parse,
                PMap(lambda s: s[1],
                     Chain(lbr_lit, parser, rbr_lit))),
        Options(and_lit, or_lit, except_lit),
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
    parser = Chain(ASExpr.parse,
                   optional(RouterExpr.parse),
                   optional(PMap(lambda s: s[1],
                                 Chain(at_lit, RouterExpr.parse))))

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


peering_ref_parser = Options(
    PeeringSpec.parse,
    PeeringSetRef.parse)

# Import


class ImportFactor(SyntaxNode):
    peerings_parser = PMap(
        lambda r: (r[1], r[2]),
        Chain(from_lit, peering_ref_parser,
              optional(PMap(
                  lambda r: r[1],
                  Chain(action_lit, actions_parser)))))
    parser = Chain(
        Many(peerings_parser),
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
    parser = Chain(lbr_lit, Many(ImportFactor.parse), rbr_lit)

    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return f"ImportFactorList({self.children!r})"

    def __str__(self):
        return "{ " + " ".join(map(str, self.children)) + " }"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[1]), s

    def sub_nodes(self):
        yield from self.children

    def __iter__(self):
        yield from self.children


import_term_parser = Options(
    ImportFactor.parse,
    ImportFactorList.parse)

import_expr_parser = Forward(lambda: ImportExpr.parse)


class ImportExpr(SyntaxNode):
    parser = Options(
        Forward(lambda: ImportExceptExpr.parse),
        Forward(lambda: ImportRefineExpr.parse),
        import_term_parser)

    @classmethod
    def parse(cls, s):
        return cls.parser(s)


class ImportExceptExpr(ImportExpr):
    parser = Chain(import_term_parser, except_lit, import_expr_parser)

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
    parser = Chain(import_term_parser, refine_lit, import_expr_parser)

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
    parser = Chain(optional(Chain(protocol_lit, ObjectRef.parse)),
                   optional(Chain(into_lit, ObjectRef.parse)),
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
    peerings_parser = PMap(
        lambda r: (r[1], r[2]),
        Chain(to_lit, peering_ref_parser,
              optional(PMap(
                  lambda r: r[1],
                  Chain(action_lit, actions_parser)))))
    parser = Chain(
        Many(peerings_parser),
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
            s += f"to {peering} "
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
    parser = Chain(lbr_lit, Many(ExportFactor.parse), rbr_lit)

    def __init__(self, children):
        self.children = list(children)

    def __repr__(self):
        return f"ExportFactorList({self.children!r})"

    def __str__(self):
        return "{ " + " ".join(map(str, self.children)) + " }"

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[1]), s

    def sub_nodes(self):
        yield from self.children

    def __iter__(self):
        yield from self.children


export_term_parser = Options(
    ExportFactor.parse,
    ExportFactorList.parse)

export_expr_parser = Forward(lambda: ExportExpr.parse)


class ExportExpr(SyntaxNode):
    parser = Options(
        Forward(lambda: ExportExceptExpr.parse),
        Forward(lambda: ExportRefineExpr.parse),
        export_term_parser)

    @classmethod
    def parse(cls, s):
        return cls.parser(s)


class ExportExceptExpr(ExportExpr):
    parser = Chain(export_term_parser, except_lit, export_expr_parser)

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
    parser = Chain(export_term_parser, refine_lit, export_expr_parser)

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
    parser = Chain(optional(Chain(protocol_lit, ObjectRef.parse)),
                   optional(Chain(into_lit, ObjectRef.parse)),
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
    parser = Chain(to_lit, peering_ref_parser,
                   optional(Chain(action_lit, actions_parser)),
                   optional(Chain(networks_lit, filter_parser)),
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
    parser = Chain(have_components_lit, PrefixSet.parse)

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
    parser = Chain(exclude_lit, PrefixSet.parse)

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
    parser = SepBy(Options(
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
    parser = SepBy(InjectAnd.parser, or_lit)

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
    expression_parser = Chain(
        Many(Chain(at_lit, RouterExpr.parse)),
        optional(Chain(action_lit, actions_parser)),
        optional(Chain(upon_lit, inject_condition_parser)))
    parser = Chain(expression_parser, eof)

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
afi_parser = Chain(afi_lit, afi_value_lit)


class AFI(SyntaxNode):
    parser = Chain(afi_lit, afi_value_lit)

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

# TODO Implement correct MP syntax


class MPImportPolicy(ImportPolicy):
    parser = Chain(AFI.parse, ImportPolicy.parse)

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
    parser = Chain(AFI.parse, ExportPolicy.parse)

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


class MPDefaultPolicy(DefaultPolicy):
    parser = Chain(AFI.parse, DefaultPolicy.parse)

    def __init__(self, afi, peering, action, filter_):
        super().__init__(peering, action, filter_)
        self.afi = afi

    @classmethod
    def parse(cls, s):
        r, s = cls.parser(s)
        return cls(r[0], r[1].peering, r[1].action, r[1].filter), s

    def __repr__(self):
        return f"MPDefaultPolicy({self.afi!r}, {self.expression!r}, " + \
            f"{self.action!r}, {self.filter!r})"

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
mp_default_parser = MPDefaultPolicy.parse


def extract_ast(node):
    sub_nodes = []
    for sub_node in node.sub_nodes():
        if isinstance(sub_node, SyntaxNode):
            sub_nodes.append(extract_ast(sub_node))
        else:
            sub_nodes.append(sub_node)
    return (str(node), sub_nodes)


def extract_refs(node):
    if not isinstance(node, SyntaxNode):
        return set()
    if isinstance(node, ObjectRef):
        return {node}
    refs = set()
    for sub_node in node.sub_nodes():
        refs |= extract_refs(sub_node)
    return refs

# TODO Implement dictionary syntax

# Parsers for several object fields


as_set_members_parser = SepBy(Options(ASSetRef.parse, ASRef.parse), comma_lit)


def as_set_members_parse(seq: str) -> str:
    res, seq = as_set_members_parser(seq)
    _, seq = eof(seq)
    return res


# TODO Implement prefix ranges after route set names
route_set_members_parser = SepBy(Options(AddressPrefixRange.parse,
                                         RouteSetRef.parse), comma_lit)


def route_set_members_parse(seq: str) -> str:
    res, seq = route_set_members_parser(seq)
    _, seq = eof(seq)
    return res


rtr_set_members_parser = SepBy(Options(RouterRef.parse,
                                       RouterSetRef.parse,
                                       ip_address_parser), comma_lit)


def rtr_set_members_parse(seq: str) -> str:
    res, seq = rtr_set_members_parser(seq)
    _, seq = eof(seq)
    return res


mbrs_by_ref_parser = SepBy(Options(MntnerRef.parse,
                                   any_lit), comma_lit)


def mbrs_by_ref_parse(seq: str) -> str:
    res, seq = mbrs_by_ref_parser(seq)
    _, seq = eof(seq)
    return res


if __name__ == "__main__":
    import argparse
    import sys
    import pprint

    argparser = argparse.ArgumentParser()
    argparser.add_argument("type", choices=("import", "export", "mp-import",
                                            "mp-export", "filter", "inject",
                                            "prefix-set", "as-regex",
                                            "peering", "router", "default",
                                            "mp-default"))
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
        "mp-default": mp_default_parser,
    }

    r, s = parsers[args.type](r)

    if args.output == "str":
        print(r)
    elif args.output == "repr":
        print(repr(r))
    elif args.output == "ast":
        pprint.pprint(extract_ast(r))
