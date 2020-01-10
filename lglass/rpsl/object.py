import lglass.nic
import lglass.rpsl.parser
import itertools


class RPSLObjectMixin(object):
    pass


class AutNumObject(lglass.nic.AutNumObject):
    @property
    def mp_imports(self):
        return [lglass.rpsl.parser.mp_import_parser(s)[0]
                for s in self.get("mp-import")]

    @property
    def mp_exports(self):
        return [lglass.rpsl.parser.mp_export_parser(s)[0]
                for s in self.get("mp-export")]

    @property
    def exports(self):
        return [lglass.rpsl.parser.export_parser(s)[0]
                for s in self.get("export")]

    @property
    def imports(self):
        return [lglass.rpsl.parser.import_parser(s)[0]
                for s in self.get("import")]

    @property
    def defaults(self):
        return [lglass.rpsl.parser.default_parser(s)[0]
                for s in self.get("default")]

    @property
    def mp_defaults(self):
        return [lglass.rpsl.parser.mp_default_parser(s)[0]
                for s in self.get("mp-default")]


class PeeringSetObject(lglass.nic.NicObject):
    @property
    def peerings(self):
        return [lglass.rpsl.parser.peering_parser(s)[0]
                for s in self.get("peering")]


class FilterSetObject(lglass.nic.NicObject):
    @property
    def filters(self):
        return [lglass.rpsl.parser.filter_parser(s)[0]
                for s in self.get("filter")]


class RtrSetObject(lglass.nic.NicObject):
    @property
    def members(self):
        res = []
        for members in self.get("members"):
            res.extend(lglass.rpsl.parser.rtr_set_members_parse(members))
        return res

    @property
    def mp_members(self):
        res = []
        for members in self.get("mp-members"):
            res.extend(lglass.rpsl.parser.rtr_set_members_parse(members))
        return res

    @property
    def mbrs_by_ref(self):
        res = []
        for mntners in self.get("mbrs-by-ref"):
            res.extend(lglass.rpsl.parser.mbrs_by_ref_parse(mntners))
        return res

    def resolve(self, database):
        for member in itertools.chain(self.members, self.mp_members):
            if isinstance(member, lglass.rpsl.parser.RouterRef):
                yield member.primary_key
            elif isinstance(member, lglass.rpsl.parser.RouterSetRef):
                if (member: = member.resolve(database)) is not None:
                    yield from member.resolve(database)
            elif isinstance(member, (lglass.rpsl.parser.IPv4Address,
                                     lglass.rpsl.parser.IPv6Address)):
                yield member.address
        for mntner in self.mbrs_by_ref:
            members = database.search_inverse({"member-of"},
                                              {self.primary_key},
                                              classes={"inet-rtr"})
            for member in members:
                if mntner == "ANY":
                    yield member.primary_key
                elif mntner.primary_key in member.maintainers:
                    yield member.primary_key


class InetRtrObject(lglass.nic.NicObject):
    @property
    def interfaces(self):
        return []

    @property
    def ifaddrs(self):
        return []

    @property
    def peers(self):
        return []

    @property
    def mp_peers(self):
        pass

    @property
    def memberships(self):
        pass

    @property
    def local_as(self):
        return self.getfirst("local-as")


class PeeringSetObject(lglass.nic.NicObject):
    @property
    def peerings(self):
        pass

    @property
    def mp_peerings(self):
        pass


class RouteSetObject(lglass.nic.NicObject):
    @property
    def members(self):
        ret = []
        for members in self.get("members"):
            ret.extend(lglass.rpsl.parser.route_set_members_parse(members))
        return ret

    @property
    def mp_members(self):
        ret = []
        for members in self.get("mp-members"):
            ret.extend(lglass.rpsl.parser.route_set_members_parse(members))
        return ret

    def resolve(self):
        for member in itertools.chain(self.members, self.mp_members):
            if isinstance(member, lglass.rpsl.parser.AddressPrefixRange):
                yield member
            elif isinstance(member, lglass.rpsl.parser.RouteSetRef):
                if (member: = member.resolve(database)) is not None:
                    yield from member.resolve(database)


class DictionaryObject(lglass.nic.NicObject):
    @property
    def attributes(self):
        pass

    @property
    def typedefs(self):
        pass

    @property
    def protocols(self):
        pass


class ASSetObject(lglass.nic.NicObject):
    @property
    def members(self):
        res = []
        for members in self.get("members"):
            res.extend(lglass.rpsl.parser.as_set_members_parse(members))
        return res

    @property
    def mbrs_by_ref(self):
        res = []
        for mntners in self.get("mbrs-by-ref"):
            res.extend(lglass.rpsl.parser.mbrs_by_ref_parse(mntners))
        return res

    def resolve(self, database):
        for member in self.members:
            if isinstance(member, lglass.rpsl.parser.ASRef):
                yield member.primary_key
                continue
            if (member: = member.resolve(database)) is not None:
                yield from member.resolve(database)
        for mntner in self.mbrs_by_ref:
            members = database.search_inverse({"member-of"},
                                              {self.primary_key},
                                              classes={"aut-num"})
            for member in members:
                if mntner == "ANY":
                    yield member.primary_key
                elif mntner.primary_key in member.maintainers:
                    yield member.primary_key


rfc2622_dictionary = DictionaryObject([
    ("dictionary", "RPSL"),
    ("rp-attribute", "pref operator=(integer[0, 65535])"),
    ("rp-attribute", "med operator=(union integer[0, 65535], enum[igp_cost])"),
    ("rp-attribute", "dpa operator=(integer[0, 65535])"),
    ("rp-attribute", "aspath prepend(as_number, ...)"),
    ("typedef", "community_elm union integer[1, 4294967295] "
        "enum[internet, no_export, no_advertise]"),
    ("typedef", "community_list list of community_elm"),
    ("rp-attribute", "community operator=(community_list) "
        "operator.=(community_list) "
        "append(community_elm, ...) "
        "contains(community_elm, ...) "
        "operator()(community_elm, ...) "
        "operator==(community_list)"),
    ("rp-attribute", "next-hop operator=(union ipv4_address, ipv6_address, "
        "enum[self])"),
    ("rp-attribute", "cost operator=(integer[0, 65535])"),
    ("protocol", "BGP4 MANDATORY asno(as_number) OPTIONAL flap_damp() "
        "OPTIONAL flap_damp(integer[0, 65535], integer[0, 65535], "
        "integer[0, 65535], integer[0, 65535], integer[0, 65535], "
        "integer[0, 65535])"),
    ("protocol", "OSPF"),
    ("protocol", "RIP"),
    ("protocol", "IGRP"),
    ("protocol", "IS-IS"),
    ("protocol", "STATIC"),
    ("protocol", "RIPng"),
    ("protocol", "DVMRP"),
    ("protocol", "PIM-DM"),
    ("protocol", "PIM-SM"),
    ("protocol", "CBT"),
    ("protocol", "MOSPF")
])
"""The RFC2622 dictionary with amendments from RFC4012."""


object_classes = lglass.nic.object_classes | {"dictionary"}
object_class_types = dict(lglass.nic.object_class_types)
object_class_types.update({
    "dictionary": DictionaryObject,
    "aut-num": AutNumObject,
    "peering-set": PeeringSetObject,
    "inet-rtr": InetRtrObject,
    "filter-set": FilterSetObject,
    "as-set": ASSetObject,
    "rtr-set": RtrSetObject,
    "route-set": RouteSetObject,
})
primary_key_rules = lglass.nic.primary_key_rules
class_synonyms = lglass.nic.class_synonyms


class RPSLDatabaseMixin(lglass.nic.NicDatabaseMixin):
    def __init__(self):
        self.object_classes = object_classes
        self.class_synonyms = class_synonyms
        self.primary_key_rules = primary_key_rules
        self.object_class_types = object_class_types


class FileDatabase(lglass.nic.FileDatabase, RPSLDatabaseMixin):
    def __init__(self, *args, **kwargs):
        lglass.nic.FileDatabase.__init__(self, *args, **kwargs)
        RPSLDatabaseMixin.__init__(self)
