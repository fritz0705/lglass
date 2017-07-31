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

def _hint_match(hint, query):
    return re.match(hint, query)

class WhoisEngine(object):
    _schema_cache = None
    cidr_classes = {"inetnum", "inet6num"}
    route_classes = {"route", "route6"}
    handle_classes = {"person", "role", "organisation"}
    network_classes = cidr_classes | route_classes
    abuse_classes = {"inetnum", "inet6num", "aut-num"}

    def __init__(self, database=None, use_schemas=False, type_hints=None):
        self.database = database
        self.use_schemas = use_schemas
        self._schema_cache = {}
        self.type_hints = {}
        if type_hints is not None:
            self.type_hints.update(type_hints)

    def filter_classes(self, classes):
        if classes is None:
            classes = self.database.object_classes
        elif isinstance(classes, str):
            classes = {classes}
        classes = set(classes).intersection(self.database.object_classes)
        return classes

    @property
    def _schemas(self):
        if self._schema_cache is None:
            self._schema_cache = {obj.key: obj for obj in self.database.find(types="schema")}
        return self._schema_cache

    def query(self, query, classes=None, reverse_domain=False, recursive=True,
            less_specific_levels=0, exact_match=False):
        primary_results = set(self.query_primary(query, classes=classes))

        def _reverse_domains(p):
            for obj in p:
                yield obj
                if reverse_domain and obj.object_class in self.cidr_classes:
                    yield from self.query_reverse_domains(obj)
        primary_results = _reverse_domains(primary_results)

        results = {}
        for obj in primary_results:
            results[obj] = [obj]

        for obj in results.keys():
            # Perform secondary lookups
            if less_specific_levels != 0:
                ls = list(self.query_less_specifics(obj, levels=less_specific_levels))
                for o in sorted(ls, key=lambda o: o.ip_network.prefixlen)[::-1]:
                    results[obj].append(o)
            if recursive:
                results[obj].extend(self.query_inverse(obj))

        for obj in results.keys():
            results[obj] = _uniq(results[obj])
        
        return results

    def query_primary(self, query, classes=None, exact_match=False):
        classes = self.filter_classes(classes)

        if re.match(r"AS[0-9]+$", query):
            # aut-num lookup
            if "aut-num" in classes:
                yield from self.database.find(keys=query, types="aut-num")
            asn = lglass.nic.parse_asn(query)
            if "as-block" in classes:
                for as_block in self.database.find(types="as-block"):
                    if asn in as_block:
                        yield as_block
            return
        elif parse_as_block(query) and "as-block" in classes:
            yield from self.database.find(keys=query, types="as-block")
            return
        elif query.startswith("ORG-") and "organisation" in classes:
            yield from self.database.find(keys=query, types="organisation")
            return
        elif query.endswith("-MNT") and "mntner" in classes:
            yield from self.database.find(keys=query, types="mntner")
            return
        elif query.startswith("AS-") and "as-set" in classes:
            yield from self.database.find(keys=query, types="as-set")
            return
        elif query.startswith("RS-") and "route-set" in classes:
            yield from self.database.find(keys=query, types="route-set")
            return
        elif query.startswith("RTRS-") and "rtr-set" in classes:
            yield from self.database.find(keys=query, types="rtr-set")
            return
        elif query.startswith("FLTR-") and "filter-set" in classes:
            yield from self.database.find(keys=query, types="filter-set")
            return
        elif query.startswith("PRNG-") and "peering-set" in classes:
            yield from self.database.find(keys=query, types="peering-set")
            return
        elif query.startswith("IRT-") and "irt" in classes:
            yield from self.database.find(keys=query, types="irt")
            return

        try:
            net = netaddr.IPNetwork(query)
            yield from self.query_network(net, classes=classes, exact_match=False)
            return
        except netaddr.core.AddrFormatError:
            pass
        
        for hint, typ in self.type_hints.items():
            if _hint_match(hint, query):
                yield from self.database.find(keys=query, types=typ)
                return
        
        yield from self.database.find(keys=query, types=classes)

    def query_network(self, net, classes=None, exact_match=False):
        if classes is None:
            classes = self.network_classes
        else:
            classes = set(classes).intersection(self.network_classes)

        inetnum_classes = self.cidr_classes.intersection(classes)
        route_classes = self.route_classes.intersection(classes)

        if not isinstance(net, netaddr.IPNetwork):
            net = netaddr.IPNetwork(net)
        desired_nets = {str(n) for n in net.supernet()} | {str(net)}

        inetnums = self.database.lookup(types=inetnum_classes, keys=desired_nets)
        routes = self.database.lookup(types=route_classes,
                keys=lambda k: k.startswith(tuple(desired_nets)))

        inetnums = sorted(list(inetnums),
                key=lambda s: netaddr.IPNetwork(s[1]).prefixlen,
                reverse=True)
        if inetnums:
            inetnum = self.database.fetch(*inetnums[0])
            if not exact_match or inetnum.ip_network == net:
                yield inetnum
        for route_spec in routes:
            route = self.database.fetch(*route_spec)
            if net in route.ip_network:
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
        else:
            # Use default rules
            inverse_objects = set()
            inverse_objects.update(obj.get("admin-c"))
            inverse_objects.update(obj.get("tech-c"))
            inverse_objects.update(obj.get("zone-c"))
            inverse_objects.update(obj.get("org"))
            for inverse in inverse_objects:
                yield from self.database.find(types=self.handle_classes,
                        keys=inverse)

    def query_abuse(self, obj):
        if obj.object_class not in self.abuse_classes:
            return
        abuse_contact_key = None
        if "abuse-c" in obj:
            abuse_contact_key = obj["abuse-c"]
        elif "org" in obj:
            org = self.database.fetch("organisation", obj["org"])
            if "abuse-c" in org:
                abuse_contact_key = org["abuse-c"]
            elif "abuse-mailbox" in org:
                return org["abuse-mailbox"]
        if not abuse_contact_key:
            return
        try:
            abuse_contact = next(self.database.find(types=self.handle_classes,
                    keys=abuse_contact_key))
        except IndexError:
            return
        if not abuse_contact:
            return
        if "abuse-mailbox" in abuse_contact:
            return abuse_contact["abuse-mailbox"]

    def query_reverse_domains(self, obj):
        for subnet, domain in lglass.dns.rdns_subnets(obj.ip_network):
            try:
                yield self.database.fetch("domain", domain)
            except KeyError:
                pass

    def query_less_specifics(self, obj, levels=1):
        if obj.type not in self.cidr_classes:
            return
        found = 0
        for supernet in obj.ip_network.supernet()[::-1]:
            try:
                res = self.database.fetch(obj.type, str(supernet))
            except KeyError:
                continue
            if res:
                yield res
                found += 1
            if found == levels:
                break

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
    argparser.add_argument("--classes", "-T", help="Comma-separated list of classes", default="")
    argparser.add_argument("--levels", "-l", help="Maximum number of less specific matches", dest="levels", type=int, default=0)
    argparser.add_argument("--exact", "-x", help="Only exact number matches", action="store_true", default=False)
    argparser.add_argument("--no-recurse", "-r", help="Disable recursive lookups for contacts", dest="recursive", action="store_false", default=True)
    argparser.add_argument("--primary-keys", "-K", help="Only return primary keys", action="store_true", default=False)
    argparser.add_argument("terms", nargs="+")

    args = argparser.parse_args()

    db = lglass.dn42.DN42Database(args.database)
    eng = WhoisEngine(db)

    classes = args.classes.split(",") if args.classes else db.object_classes

    query_args = dict(
            reverse_domain=args.domains,
            classes=classes,
            less_specific_levels=args.levels,
            exact_match=args.exact,
            recursive=args.recursive)

    if args.primary_keys:
        query_args["recursive"] = False

    pretty_print_options = dict(
            min_padding=16,
            add_padding=0)

    start_time = time.time()
    for term in args.terms:
        print("% Results for query '{query}'".format(query=term))
        print()
        results = eng.query(term, **query_args)
        for primary in sorted(results.keys(), key=lambda k: k.type):
            related = list(results[primary])[1:]
            if args.primary_keys:
                if isinstance(db.primary_key_rules.get(primary.type), list):
                    for key in db.primary_key_rules[primary.type]:
                        print("{}: {}".format(key, primary[key]))
                else:
                    print("{}: {}".format(primary.type, primary.key))
                print()
                continue
            print("% Information related to '{obj}'".format(
                obj=db.primary_key(primary)))
            print()
            abuse_contact = eng.query_abuse(primary)
            if abuse_contact:
                print("% Abuse contact for '{obj}' is '{abuse}'".format(
                    obj=db.primary_key(primary),
                    abuse=abuse_contact))
                print()
            print("".join(primary.pretty_print(**pretty_print_options)))
            for obj in sorted(related, key=lambda k: k.type):
                print("".join(obj.pretty_print(**pretty_print_options)))
    print("% Query took {} seconds".format(time.time() - start_time))

    #print(eng._schemas)

