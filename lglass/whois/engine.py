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
            if less_specific_levels != 0:
                for ls in self.query_less_specifics(obj,
                        levels=less_specific_levels):
                    results[obj].append(ls)
            # Perform secondary lookups
            pass
        
        return results

    def query_primary(self, query, types=None, exact_match=False):
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
                if not inetnum and not exact_match:
                    for snet in net.supernet()[::-1]:
                        inetnum = self.database.try_fetch(inetnum_type, str(snet))
                        if inetnum:
                            yield inetnum
                            break
                elif inetnum:
                    yield inetnum
            if route_types:
                routes = list(self.database.find(filter=lambda o: o.key == net_str,
                        keys=lambda k: k.startswith(net_str),
                        types=route_types))
                if not routes:
                    for snet in supernets:
                        routes = list(self.database.find(filter=lambda o: o.key == str(snet),
                                keys=lambda k: k.startswith(str(snet)),
                                types=route_types))
                        if routes:
                            break
                yield from routes
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

    def query_less_specifics(self, obj, levels=1):
        if obj.type not in {"inetnum", "inet6num"}:
            return

        found = 0
        for supernet in lglass.object.cidr_key(obj).supernet()[::-1]:
            res = self.database.try_fetch(obj.type, str(supernet))
            if res:
                yield res
                found += 1
            if found == levels:
                break

    def _as_blocks(self):
        for typ, key in self.database.lookup(types="as-block"):
            try:
                lower, upper = parse_as_block(key)
                yield (range(lower, upper), key)
            except ValueError:
                pass

if __name__ == "__main__":
    import argparse
    import time

    import lglass.dn42

    argparser = argparse.ArgumentParser(description="Perform whois lookups directly")
    argparser.add_argument("--database", "-d", help="Path to database", default=".")
    argparser.add_argument("--domains", "-D", help="Include reverse domains", action="store_true", default=False)
    argparser.add_argument("--types", "-T", help="Comma-separated list of types", default="")
    argparser.add_argument("--levels", "-L", help="Maximum number of less specific matches", dest="levels", type=int, default=1)
    argparser.add_argument("--exact", "-x", help="Only exact number matches", action="store_true", default=False)
    argparser.add_argument("terms", nargs="+")

    args = argparser.parse_args()

    db = lglass.dn42.DN42Database(args.database)
    eng = WhoisEngine(db)

    types = args.types.split(",") if args.types else db.object_types

    query_args = dict(
            reverse_domain=args.domains,
            types=types,
            less_specific_levels=args.levels,
            exact_match=args.exact)

    start_time = time.time()
    for term in args.terms:
        print("% Results for query '{query}'".format(query=term))
        print()
        for pobj, related in eng.query(term, **query_args).items():
            print("% Information related to '{obj}'".format(obj=db._primary_key(pobj)))
            print()
            for obj in related:
                print(obj)
    print("% Query took {} seconds".format(time.time() - start_time))

