# coding: utf-8

import os

import netaddr

import lglass.object
import lglass.database
import lglass.dns

class DN42Object(lglass.object.Object):
    @property
    def type(self):
        if self.data[0][0] == "domain":
            return "dns"
        return self.data[0][0]

    @property
    def key(self):
        if self.type in {"inet6num", "route6"}:
            return range_to_network(self.data[0][1])
        return self.data[0][1]

    @property
    def cidr(self):
        if self.type in {"inetnum", "route"}:
            return netaddr.IPNetwork(range_to_network(self.key))
        return netaddr.IPNetwork(self.key)

    def to_domain_objects(self):
        if self.type not in {"inetnum", "inet6num"}:
            raise NotImplementedError("Not implemented.")
        network = self.cidr
        if network.version == 4 and network.prefixlen > 24:
            # TODO handle sub-/24 allocations
            pass
        else:
            next_prefixlen = 8 * ((network.prefixlen - 1) // 8 + 1) if network.version == 4 else 4 * ((network.prefixlen - 1) // 4 + 1)
            for subnet in network.subnet(next_prefixlen):
                obj = DN42Object([("domain", lglass.dns.rdns_domain(subnet))])
                obj.extend(list(self.items()))
                yield obj

class DN42Database(lglass.database.SimpleDatabase):
    version = 0

    def __init__(self, path):
        lglass.database.SimpleDatabase.__init__(self, path)
        self.reload()

    def reload(self):
        try:
            with open(os.path.join(self._path, "DatabaseVersion")) as fh:
                version = 1
        except FileNotFoundError:
            version = 0
        if version == 0:
            self.object_types = set(self.object_types)
            self.object_types.remove("domain")
            self.object_types.add("dns")

    def fetch(self, typ, key):
        if self.version == 0 and typ == "domain" and key.endswith("ip6.arpa") or key.endswith("in-addr.arpa"):
            return self._fetch_rdns_domain(key)
        obj = super().fetch(typ, key)
        if self.version == 0 and self._intrinsic_type(obj.type) in {"inet6num", "route6", "dns", "inetnum"}:
            return DN42Object(obj)
        return obj

    def _fetch_rdns_domain(self, key):
        try:
            return super().fetch("dns", key)
        except KeyError:
            pass
        net = lglass.dns.rdns_network(key)
        try:
            # First, do a CIDR lookup for our determined network
            inetnums = lglass.database.cidr_lookup(self, net, allowed_types={"inetnum", "inet6num"})
            # Then, sort by prefix length
            inetnums = map(lambda x: (x[0], netaddr.IPNetwork(x[1])), inetnums)
            inetnums = sorted(inetnums, key=lambda c: c[1].prefixlen, reverse=True)
            inetnums = map(lambda x: (x[0], str(x[1])), inetnums)
            inetnum = self.fetch(*next(inetnums))
            if inetnum.cidr.prefixlen not in range(net.prefixlen - 8 + 1, net.prefixlen + 1):
                raise KeyError
            for domain in inetnum.to_domain_objects():
                if domain.key == key:
                    return domain
        except (KeyError, StopIteration):
            pass
        except netaddr.core.AddrFormatError:
            pass
        raise KeyError(repr(("domain", key)))

    def save(self, obj):
        if isinstance(obj, DN42Object) and self.version > 0:
            # TODO handle database updates
            pass
        super().save(obj)

    def _lookup_type(self, typ, keys):
        if self.version == 0 and typ == "dns":
            yield from self._lookup_domain(keys)
        yield from super()._lookup_type(typ, keys)

    def _lookup_domain(self, keys):
        for inetnum in self.lookup(types={"inetnum", "inet6num"}):
            try:
                inetnum = self.fetch(*inetnum)
                for domain in inetnum.to_domain_objects():
                    if lglass.database.perform_key_match(keys, domain.key):
                        yield ("dns", domain.key)
            except netaddr.core.AddrFormatError:
                pass

def range_to_network(rng):
    lower, upper = rng.split("-", 1)
    lower = lower.strip()
    upper = upper.strip()
    return str(netaddr.IPRange(lower, upper).cidrs()[0])

