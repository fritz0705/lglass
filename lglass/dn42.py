# coding: utf-8

import os

import netaddr

import lglass.dns
import lglass.nic


def _format_as_block_key(obj):
    return "{}_{}".format(obj.start, obj.end)


def fix_object(obj):
    if obj.object_class in {"route", "route6"}:
        for origin in obj.get("origin"):
            nobj = lglass.nic.RouteObject(obj)
            nobj.remove("origin")
            nobj.insert(1, "origin", origin)
            yield nobj
    elif obj.object_class == "as-block":
        nobj = lglass.nic.ASBlockObject(obj)
        nobj.object_key = nobj.primary_key
        yield nobj
    elif obj.object_class in {"inetnum", "inet6num"}:
        nobj = InetnumObject(obj)
        if obj.object_class == "inet6num":
            nobj.object_key = nobj.primary_key
        nobj.remove("nserver")
        nobj.remove("ds-rdata")
        yield nobj
    else:
        yield obj


class InetnumObject(lglass.nic.InetnumObject):
    def to_domain_objects(self):
        if "nserver" not in self:
            return
        for _, rdns_domain in self.rdns_domains():
            obj = DomainObject([("domain", rdns_domain)])
            for k, v in self.items():
                if k in {"zone-c", "admin-c", "tech-c", "mnt-by", "nserver",
                         "ds-rdata", "created", "last-modified", "source"}:
                    obj.add(k, v)
            yield obj


class DomainObject(lglass.nic.NicObject):
    pass


class DN42Database(lglass.nic.FileDatabase):
    version = 0

    def __init__(self, path, force_version=None):
        lglass.nic.FileDatabase.__init__(self, path)
        self.object_class_types = dict(self.object_class_types)
        self.object_class_types.update({
            "domain": DomainObject,
            "inetnum": InetnumObject,
            "inet6num": InetnumObject
        })
        self._domain_cache = {}
        try:
            with open(os.path.join(self._path, "DatabaseVersion")) as fh:
                self.version = int(fh.read())
        except FileNotFoundError:
            if "dn42-version" in self.manifest:
                self.version = int(self.manifest["dn42-version"])
            else:
                self.version = 0
        except ValueError:
            self.version = 1
        if force_version is not None:
            self.version = force_version
        if self.version == 0:
            self.object_classes = set(self.object_classes)
            self.object_classes.remove("domain")
            self.object_classes.add("dns")
            self.primary_key_rules = dict(self.primary_key_rules)
            self.primary_key_rules["route"] = ["route"]
            self.primary_key_rules["route6"] = ["route6"]
            self.primary_key_rules["as-block"] = _format_as_block_key

    def flush_cache(self):
        self._domain_cache = {}

    def preload_domains(self):
        existing_domains = {
            domain for _,
            domain in super().lookup(
                types="dns")}
        inetnums = list(self.find(types={"inetnum", "inet6num"}))
        inetnums = sorted(inetnums,
                          key=lambda d: d.ip_network.prefixlen,
                          reverse=True)
        for inetnum in inetnums:
            for domain in inetnum.to_domain_objects():
                if domain in existing_domains:
                    continue
                if domain.object_key in self._domain_cache:
                    continue
                self._domain_cache[domain.object_key] = domain

    def fetch(self, object_class, object_key):
        object_class = self.primary_class(object_class)
        if self.version == 0 and object_class == "dns":
            return self._fetch_dns(object_key)
        return super().fetch(object_class, object_key)

    def _fetch_dns(self, object_key):
        try:
            return super().fetch("dns", object_key)
        except KeyError:
            pass
        if object_key in self._domain_cache:
            return self._domain_cache[object_key]
        network = lglass.dns.rdns_network(object_key)
        if network is None:
            raise KeyError(repr(("dns", object_key)))
        object_class = "inetnum" if network.version == 4 else "inet6num"
        for net in [network] + network.supernet()[::-1]:
            try:
                obj = self.fetch(object_class, str(net))
            except KeyError:
                continue
            for domain_object in obj.to_domain_objects():
                if object_key == domain_object.object_key:
                    self._domain_cache[object_key] = domain_object
                    return domain_object
        raise KeyError(repr(("dns", object_key)))

    def _lookup_class(self, object_class, keys):
        object_class = self.primary_class(object_class)
        if object_class == "dns" and self.version == 0:
            yield from self._lookup_dns(keys)
            return
        yield from super()._lookup_class(object_class, keys)

    def _lookup_dns(self, keys):
        if isinstance(
                keys, str) and not keys.endswith(
                ("in-addr.arpa", "ip6.arpa")):
            yield from super()._lookup_class("dns", keys)
            return
        if isinstance(keys, set):
            keys = set(keys)
            for key in frozenset(keys):
                if not key.endswith(("in-addr.arpa", "ip6.arpa")):
                    keys.remove(key)
                    yield from super()._lookup_class("dns", {key})
        if keys is not None and not keys:
            return
        found = set()
        for dns in super()._lookup_class("dns", keys):
            found.add(dns)
            yield dns
        for inetnum in self.lookup(types={"inetnum", "inet6num"}):
            try:
                inetnum = self.fetch(*inetnum)
                if inetnum.ip_network.prefixlen > 24 and \
                        inetnum.ip_network.version == 4:
                    continue
                for domain in inetnum.to_domain_objects():
                    if domain in found:
                        continue
                    self._domain_cache[domain.object_key] = domain
                    if lglass.database.perform_key_match(
                            keys, domain.object_key):
                        yield ("dns", domain.object_key)
            except netaddr.core.AddrFormatError:
                pass

    def save(self, obj, **options):
        if self.version == 1:
            for nobj in fix_object(obj):
                super().save(nobj, **options)
            return
        super().save(nobj, **options)
