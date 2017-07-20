# coding: utf-8

import argparse
import re

import jinja2
import netaddr

import lglass.database
import lglass.dns

def parse_aut_num(aut_num):
    m = re.match(r"(AS)?([0-9]+)$", aut_num)
    return int(m[2])

def parse_as_block(as_block):
    m = re.match(r"(AS)?([0-9]+)[-_](AS)?([0-9]+)$", as_block)
    return int(m[2]), int(m[4])

class WhoisEngine(object):
    def __init__(self, database=None, use_schemas=False, allow_wildcards=False):
        self.database = database
        self.use_schemas = use_schemas
        self.allow_wildcards = allow_wildcards

    def query(self, query, types=None, reverse_domain=False, recursive=True,
            less_specific_levels=1, exact_match=False):
        primary_results = self.query_primary(query, types=types)

        if exact_match:
            def _filter_exacts(obj):
                pass
            primary_results = filter(_filter_exacts, primary_results)

        def _reverse_domains(p):
            for obj in p:
                yield obj
                if reverse_domain and obj.type in {"inetnum", "inet6num"}:
                    yield from self.query_reverse_domains(obj)
        primary_results = _reverse_domains(primary_results)

        results = {}
        for obj in primary_results:
            results[obj] = [obj]

        for obj in results.keys():
            # Perform secondary lookups
            pass
        
        return results

    def query_primary(self, query, types=None):
        if types is None:
            types = self.database.object_types
        else:
            types = set(types).intersection(self.database.object_types)

        if re.match(r"AS[0-9]+$", query):
            # aut-num lookup
            if "aut-num" in types:
                yield from self.database.find(keys=query, types="aut-num")
            if "as-block" in types:
                aut_num = int(query[2:])
                for block, key in self._as_blocks():
                    if aut_num in block:
                        yield self.database.fetch("as-block", key)
            return
        elif re.match(r"(AS)?[0-9]+\s*-\s*(AS)?[0-9]+$", query) and "as-block" in query:
            yield fromself.database.find(keys=query, types="as-block")
            return
        elif query.startswith("ORG-") and "organisation" in types:
            yield from self.database.find(keys=query, types="organisation")
            return
        elif query.endswith("-MNT") and "mntner" in types:
            yield from self.database.find(keys=query, types="mntner")
            return

        try:
            net = netaddr.IPNetwork(query)
            inetnum_types = types.intersection({"inetnum", "inet6num"})
            route_types = types.intersection({"route", "route6"})
            supernets = net.supernet()
            net_str = str(net)
            # Primary address lookup, only find first matching objects
            # TODO fix
            for inetnum_type in inetnum_types:
                inetnum = self.database.try_fetch(inetnum_type, net_str)
                if not inetnum:
                    for snet in net.supernet()[::-1]:
                        inetnum = self.database.try_fetch(inetnum_type, str(snet))
                        if inetnum:
                            yield inetnum
                            break
                else:
                    yield inetnum
            if route_types:
                yield from self.database.find(filter=lambda o: o.key == net_str,
                        keys=lambda k: k.startswith(net_str),
                        types=route_types)
                for snet in supernets:
                    yield from self.database.find(filter=lambda o: o.key == str(snet),
                            keys=lambda k: k.startswith(str(snet)),
                            types=route_types)
            return
        except netaddr.core.AddrFormatError:
            pass
        
        yield from self.database.find(keys=query, types=types)

    def query_inverse(self, obj):
        pass

    def query_reverse_domains(self, obj):
        cidr = lglass.object.cidr_key(obj)
        for subnet, domain in lglass.dns.rdns_subnets(cidr):
            try:
                yield self.database.fetch("domain", domain)
            except KeyError:
                pass

    def query_less_specific(self, obj):
        pass

    def _as_blocks(self):
        for typ, key in self.database.lookup(types="as-block"):
            try:
                lower, upper = parse_as_block(key)
                yield (range(lower, upper), key)
            except ValueError:
                pass

if __name__ == "__main__":
    import argparse

    import lglass.dn42

    argparser = argparse.ArgumentParser(description="Perform whois lookups directly")
    argparser.add_argument("--database", "-d", help="Path to database", default=".")
    argparser.add_argument("--domains", "-D", help="Include reverse domains", action="store_true", default=False)
    argparser.add_argument("--types", "-T", help="Comma-separated list of types", default="")
    argparser.add_argument("terms", nargs="+")

    args = argparser.parse_args()

    db = lglass.dn42.DN42Database(args.database)
    eng = WhoisEngine(db)

    types = args.types.split(",") if args.types else db.object_types

    for term in args.terms:
        print("% Results for query '{query}'".format(query=term))
        print()
        for obj in eng.query(term, reverse_domain=args.domains, types=types).keys():
            print("% Information related to '{obj}'".format(obj=db._primary_key(obj)))
            print()
            print(obj)

