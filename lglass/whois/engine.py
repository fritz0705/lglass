# coding: utf-8

import argparse
import re

import jinja2
import netaddr

import lglass.database
import lglass.dns
import lglass.schema

def parse_aut_num(aut_num):
    m = re.match(r"(AS)?([0-9]+)$", aut_num)
    return int(m[2])

def parse_as_block(as_block):
    m = re.match(r"(AS)?([0-9]+)\s*[-_]\s*(AS)?([0-9]+)$", as_block)
    if not m:
        return False
    return int(m[2]), int(m[4])

def _uniq(it):
    s = set()
    for v in it:
        if v in s: continue
        s.add(v)
        yield v

class WhoisEngine(object):
    _schema_cache = None

    def __init__(self, database=None, use_schemas=True, allow_wildcards=False):
        self.database = database
        self.use_schemas = use_schemas
        self.allow_wildcards = allow_wildcards
        self._schema_cache = {}

    @property
    def _schemas(self):
        if self._schema_cache is None:
            self._schema_cache = {obj.key: obj for obj in self.database.find(types="schema")}
        return self._schema_cache

    def query(self, query, types=None, reverse_domain=False, recursive=True,
            less_specific_levels=1, exact_match=False):
        primary_results = set(self.query_primary(query, types=types))

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
            if recursive:
                results[obj].extend(self.query_inverse(obj))
            # Perform secondary lookups
            pass

        for obj in results.keys():
            results[obj] = _uniq(results[obj])
        
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
        elif parse_as_block(query) and "as-block" in types:
            yield from self.database.find(keys=query, types="as-block")
            return
        elif query.startswith("ORG-") and "organisation" in types:
            yield from self.database.find(keys=query, types="organisation")
            return
        elif query.endswith("-MNT") and "mntner" in types:
            yield from self.database.find(keys=query, types="mntner")
            return

        try:
            net = netaddr.IPNetwork(query)
            yield from self.query_network(net, types=types, exact_match=False)
            return
        except netaddr.core.AddrFormatError:
            pass
        
        yield from self.database.find(keys=query, types=types)

    def query_network(self, net, types=None, exact_match=False):
        if types is None:
            types = {"inetnum", "inet6num", "route", "route6"}
        else:
            types = set(types).intersection({"inetnum", "inet6num", "route",
                "route6"})

        inetnum_types = {"inetnum", "inet6num"}.intersection(types)
        route_types = {"route", "route6"}.intersection(types)

        if not isinstance(net, netaddr.IPNetwork):
            net = netaddr.IPNetwork(net)
        desired_nets = {str(n) for n in net.supernet()} | {str(net)}

        inetnums = self.database.lookup(types=inetnum_types, keys=desired_nets)
        routes = self.database.lookup(types=route_types,
                keys=lambda k: k.startswith(tuple(desired_nets)))

        inetnums = sorted(list(inetnums),
                key=lambda s: netaddr.IPNetwork(s[1]).prefixlen,
                reverse=True)
        if inetnums:
            inetnum = self.database.fetch(*inetnums[0])
            if not exact_match or lglass.object.cidr_key(inetnum) == net:
                yield inetnum
        for route_spec in routes:
            route = self.database.fetch(*route_spec)
            if net in lglass.object.cidr_key(route):
                yield route

    def query_inverse(self, obj):
        if self.use_schemas:
            try:
                schema = self._load_schema(obj.type)
            except KeyError:
                return
            inverse_objects = []
            for key, _, _, inverse in schema.schema_keys():
                for value in obj.get(key):
                    yield from self.database.find(types=inverse, keys=value)
        return

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

    def _load_schema(self, typ):
        try:
            return self._schema_cache[typ]
        except KeyError:
            schema = lglass.schema.load_schema(self.database, typ)
            self._schema_cache[typ] = schema
            return schema

if __name__ == "__main__":
    import argparse
    import time

    import lglass.dn42

    argparser = argparse.ArgumentParser(description="Perform whois lookups directly")
    argparser.add_argument("--database", "-D", help="Path to database", default=".")
    argparser.add_argument("--domains", "-d", help="Include reverse domains", action="store_true", default=False)
    argparser.add_argument("--types", "-T", help="Comma-separated list of types", default="")
    argparser.add_argument("--levels", "-l", help="Maximum number of less specific matches", dest="levels", type=int, default=0)
    argparser.add_argument("--exact", "-x", help="Only exact number matches", action="store_true", default=False)
    argparser.add_argument("--no-recurse", "-r", help="Disable recursive lookups for contacts", dest="recursive", action="store_false", default=True)
    argparser.add_argument("--primary-keys", "-K", help="Only return primary keys", action="store_true", default=False)
    argparser.add_argument("terms", nargs="+")

    args = argparser.parse_args()

    db = lglass.dn42.DN42Database(args.database)
    eng = WhoisEngine(db)

    types = args.types.split(",") if args.types else db.object_types

    query_args = dict(
            reverse_domain=args.domains,
            types=types,
            less_specific_levels=args.levels,
            exact_match=args.exact,
            recursive=args.recursive)

    start_time = time.time()
    for term in args.terms:
        print("% Results for query '{query}'".format(query=term))
        print()
        results = eng.query(term, **query_args)
        for primary in sorted(results.keys(), key=lambda k: k.type):
            related = results[primary]
            print("% Information related to '{obj}'".format(obj=db._primary_key(primary)))
            print()
            if args.primary_keys:
                print("{}: {}".format(primary.type, primary.key))
                print()
                continue
            for obj in related:
                print(obj)
    print("% Query took {} seconds".format(time.time() - start_time))

    #print(eng._schemas)

