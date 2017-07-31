# coding: utf-8

import datetime
import os
import re

import dateutil.parser
import netaddr

import lglass.database
import lglass.object
import lglass.dns

def parse_asn(asn):
    try:
        return int(asn)
    except ValueError:
        pass
    m = re.match("AS([0-9]+)$", asn)
    if m:
        return int(m[1])

class NicObject(lglass.object.Object):
    @property
    def source(self):
        try:
            return self["source"]
        except KeyError:
            pass

    @property
    def maintainers(self):
        return list(self.get("mnt-by"))

    @property
    def created_at(self):
        try:
            return self["created"]
        except KeyError:
            pass

    @property
    def last_modified(self):
        try:
            return self["last-modified"]
        except KeyError:
            pass

    @last_modified.setter
    def last_modified(self, new_date):
        if isinstance(new_date, (int, float)):
            new_date = datetime.datetime.fromtimestamp(new_date, tz=datetime.timezone.utc)
        elif isinstance(new_date, str):
            new_date = dateutil.parser.parse(new_date)
        self["last-modified"] = new_date.astimezone(tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class HandleObject(NicObject):
    @property
    def primary_key(self):
        try:
            return self["nic-hdl"]
        except KeyError:
            pass

class InetnumObject(NicObject):
    @property
    def ip_range(self):
        if self.ip_version == 4:
            start, end = map(lambda s: s.strip(), self["inetnum"].split("-", 1))
            return netaddr.IPRange(start, end)
        elif self.ip_version == 6:
            if "-" in self["inet6num"]:
                start, end = self["inet6num"].split("-", 1)
                start, end = start.strip(), end.strip()
                return netaddr.IPRange(start, end)
            net = self.ip_network
            return netaddr.IPRange(net[0], net[-1])

    @property
    def ip_network(self):
        try:
            if self.ip_version == 6:
                return netaddr.IPNetwork(self["inet6num"])
        except netaddr.core.AddrFormatError:
            return self.ip_range.cidrs()[0]
        if self.ip_version == 4:
            return self.ip_range.cidrs()[0]

    @property
    def ip_version(self):
        if self.object_class == "inet6num":
            return 6
        elif self.object_class == "inetnum":
            return 4

    def rdns_domains(self):
        net = self.ip_network
        if self.ip_version == 4:
            next_prefixlen = 8 * ((net.prefixlen - 1) // 8 + 1)
        elif self.ip_version == 6:
            next_prefixlen = 4 * ((net.prefixlen - 1) // 4 + 1)
        for subnet in net.subnet(next_prefixlen):
            yield (subnet, lglass.dns.rdns_domain(subnet))

    @property
    def primary_key(self):
        return str(self.ip_network)

class ASBlockObject(NicObject):
    def __contains__(self, number_or_key):
        if isinstance(number_or_key, int):
            return number_or_key in self.range
        return NicObject.__contains__(self, number_or_key)

    @property
    def start(self):
        return self.range.start

    @property
    def end(self):
        return self.range.stop

    @property
    def range(self):
        start, end = self.object_key.split("-", 1)
        start, end = parse_asn(start.strip()), parse_asn(end.strip())
        return range(start, end + 1)

    @property
    def primary_key(self):
        return "AS{} - AS{}".format(self.start, self.end)

class RouteObject(NicObject):
    @property
    def ip_network(self):
        if self.ip_version == 6:
            return netaddr.IPNetwork(self["route6"])
        elif self.ip_version == 4:
            return netaddr.IPNetwork(self["route"])

    @property
    def ip_version(self):
        if self.object_class == "route6":
            return 6
        elif self.object_class == "route":
            return 4
    
    @property
    def origin(self):
        try:
            return self["origin"]
        except:
            pass

    @property
    def primary_key(self):
        return "{}{}".format(self.ip_network, self.origin)

object_classes = {"as-block", "as-set", "aut-num", "domain", "filter-set",
        "inet-rtr", "inet6num", "inetnum", "irt", "key-cert", "mntner",
        "organisation", "peering-set", "person", "poem", "poetic-form", "role",
        "route-set", "route", "route6", "rtr-set"}
class_synonyms = [{"dns", "domain"}]
primary_key_rules = {}
object_class_types = {
        "route": RouteObject,
        "route6": RouteObject,
        "inetnum": InetnumObject,
        "inet6num": InetnumObject,
        "person": HandleObject,
        "role": HandleObject,
        "as-block": ASBlockObject
}

class NicDatabaseMixin(object):
    def __init__(self):
        self.object_classes = object_classes
        self.class_synonyms = class_synonyms
        self.primary_key_rules = primary_key_rules
        self.object_class_types = object_class_types

    def object_class_type(self, object_class):
        try:
            return self.object_class_types[object_class]
        except KeyError:
            return NicObject

class FileDatabase(lglass.database.Database, NicDatabaseMixin):
    def __init__(self, path):
        NicDatabaseMixin.__init__(self)
        self._path = path

    def _build_path(self, object_class, object_key=None):
        if object_key is None:
            return os.path.join(self._path, object_class)
        return os.path.join(self._path, object_class, object_key.replace("/", "_"))

    def lookup(self, types=None, keys=None):
        if types is None:
            types = self.object_classes
        elif isinstance(types, str):
            types = {self.primary_class(types)}
        else:
            types = map(self.primary_class, types)
        for type in types:
            try:
                yield from self._lookup_class(type, keys)
            except FileNotFoundError:
                pass

    def _lookup_class(self, object_class, object_keys):
        for key in os.listdir(os.path.join(self._path, object_class)):
            if key[0] == '.': continue
            key = key.replace("_", "/")
            if lglass.database.perform_key_match(object_keys, key):
                yield (object_class, key)

    def fetch(self, object_class, object_key):
        object_class = self.primary_class(object_class)
        try:
            path = self._build_path(object_class, object_key)
            with open(path) as fh:
                obj = self.object_class_type(object_class).from_file(fh)
            if obj.last_modified is None:
                st = os.stat(path)
                obj.last_modified = st.st_mtime
            return obj
        except (FileNotFoundError, IsADirectoryError):
            raise KeyError(repr((object_class, object_key)))
        except ValueError as verr:
            raise ValueError((object_class, object_key), *verr.args)

    def save(self, obj, **options):
        object_class = self.primary_class(obj)
        object_key = self.primary_key(obj).replace("/", "_")
        try:
            os.mkdir(os.path.join(self._path, object_class))
        except FileExistsError:
            pass
        with open(self._build_path(object_class, object_key), "w") as fh:
            obj = NicObject(obj.data)
            obj.remove("last-modified")
            obj.remove("source")
            fh.write("".join(obj.pretty_print(**options)))
