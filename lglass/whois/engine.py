# coding: utf-8

import argparse
import re
import sys

import netaddr

import lglass.database
import lglass.dns
import lglass.nic
import lglass.schema
import lglass.proxy


def _hint_match(hint, query):
    return re.match(hint, query)


class WhoisEngine(object):
    _schema_cache = None
    cidr_classes = {"inetnum", "inet6num"}
    address_classes = {"address"}
    route_classes = {"route", "route6"}
    handle_classes = {"person", "role", "organisation"}
    network_classes = cidr_classes | route_classes | address_classes
    abuse_classes = {"inetnum", "inet6num", "aut-num"} | address_classes

    def __init__(self, database=None, use_schemas=False, type_hints=None,
                 global_cache=None, query_cache=True,
                 ipv4_more_specific_prefixlens=None,
                 ipv6_more_specific_prefixlens=None):
        self.database = database
        self.use_schemas = use_schemas
        self._schema_cache = {}
        self.type_hints = {}
        if type_hints is not None:
            self.type_hints.update(type_hints)
        self.query_cache = query_cache
        if ipv4_more_specific_prefixlens is None:
            ipv4_more_specific_prefixlens = set(range(20, 33))
        if ipv6_more_specific_prefixlens is None:
            ipv6_more_specific_prefixlens = set()
        self.ipv4_more_specific_prefixlens = ipv4_more_specific_prefixlens
        self.ipv6_more_specific_prefixlens = ipv6_more_specific_prefixlens

    def new_query_database(self):
        if self.query_cache:
            return lglass.proxy.CacheProxyDatabase(self.database)
        return self.database

    def _get_database(self, prototype):
        if prototype is not None:
            return prototype
        if self.database is not None:
            return self.new_query_database()
        raise TypeError("positional argument 'database' required for unbound"
                        " whois engine")

    def filter_classes(self, classes, *other_class_sets, database=None):
        database = self._get_database(database)
        if classes is None:
            classes = database.object_classes
        elif isinstance(classes, str):
            classes = {classes}
        else:
            classes = set(classes)
        for class_set in other_class_sets:
            classes &= class_set
        if "nic-hdl" in classes:
            classes.update(self.handle_classes)
        if "cidr" in classes:
            classes.update(self.cidr_classes)
        if "address" in classes:
            classes.update(self.address_classes)
        classes = set(database.primary_class(c)
                      for c in classes).intersection(database.object_classes)
        return classes

    def query(self, query, classes=None, reverse_domain=False, recursive=True,
              less_specific_levels=0, exact_match=False, database=None,
              more_specific_levels=0, sources=None):
        database = self._get_database(database)
        classes = self.filter_classes(classes, database=database)
        primary_classes = set(classes)
        if database.primary_class("domain") in primary_classes:
            primary_classes.update(self.cidr_classes)
        if self.address_classes & primary_classes and more_specific_levels:
            primary_classes.update(self.cidr_classes)

        if isinstance(query, dict):
            primary_results = list(
                self.query_search_inverse(
                    query,
                    classes=primary_classes,
                    database=database))
        else:
            primary_results = list(self.query_primary(query,
                                                      classes=primary_classes,
                                                      database=database,
                                                      exact_match=exact_match))

        if less_specific_levels != 0:
            for obj in list(primary_results):
                if obj.object_class in self.cidr_classes:
                    primary_results = list(
                        self.query_less_specifics(
                            obj,
                            levels=less_specific_levels,
                            database=database))[
                        ::-1] + primary_results

        if more_specific_levels != 0:
            for obj in frozenset(primary_results):
                if obj.object_class in self.cidr_classes:
                    primary_results.extend(
                        self.query_more_specifics(
                            obj,
                            levels=more_specific_levels,
                            database=database))

        if reverse_domain:
            for obj in list(primary_results):
                if obj.object_class in self.cidr_classes:
                    primary_results.extend(self.query_reverse_domains(
                        obj.ip_network,
                        database=database,
                        classes=classes))

        results = {obj: [obj]
                   for obj in primary_results
                   if database.primary_class(obj.object_class) in classes}

        for obj in results.keys():
            if recursive:
                results[obj].extend(self.query_inverse(obj, database=database))

        return results

    def query_search_inverse(self, query, classes=None, database=None):
        database = self._get_database(database)
        classes = self.filter_classes(classes)
        yield from database.search(query, classes=classes)

    def query_primary(self, query, classes=None, exact_match=False,
                      database=None):
        database = self._get_database(database)

        classes = self.filter_classes(classes, database=database)

        if re.match(r"[aA][sS][0-9]+$", query):
            # aut-num lookup
            if "aut-num" in classes:
                yield from database.find(keys=query, classes=("aut-num",))
            asn = lglass.nic.parse_asn(query)
            if "as-block" in classes:
                for as_block in database.find(classes=("as-block",)):
                    if asn in as_block:
                        yield as_block
            return
        elif lglass.nic.parse_as_block(query) and "as-block" in classes:
            k = lglass.nic.ASBlockObject([("as-block", query)])
            yield from database.find(keys=k.primary_key, classes=("as-block",))
            return
        elif query.startswith("ORG-") and "organisation" in classes:
            yield from database.find(keys=query, classes=("organisation",))
            return
        elif query.endswith("-MNT") and "mntner" in classes:
            yield from database.find(keys=query, classes=("mntner",))
            return
        elif query.startswith("AS-") and "as-set" in classes:
            yield from database.find(keys=query, classes=("as-set",))
            return
        elif query.startswith("RS-") and "route-set" in classes:
            yield from database.find(keys=query, classes=("route-set",))
            return
        elif query.startswith("RTRS-") and "rtr-set" in classes:
            yield from database.find(keys=query, classes=("rtr-set",))
            return
        elif query.startswith("FLTR-") and "filter-set" in classes:
            yield from database.find(keys=query, classes=("filter-set",))
            return
        elif query.startswith("PRNG-") and "peering-set" in classes:
            yield from database.find(keys=query, classes=("peering-set",))
            return
        elif query.startswith("IRT-") and "irt" in classes:
            yield from database.find(keys=query, classes=("irt",))
            return
        elif query.startswith("SEG-") and "segment" in classes:
            yield from database.find(keys=query, classes=("segment",))
            return

        try:
            net = netaddr.IPNetwork(query)
            yield from self.query_network(net, classes=classes,
                                          exact_match=exact_match, database=database)
            return
        except netaddr.core.AddrFormatError:
            pass
        try:
            netrange = lglass.nic.parse_ip_range(query)
            for net in netrange.cidrs():
                yield from self.query_network(net, classes=classes,
                                              exact_match=exact_match, database=database)
                pass
        except (netaddr.core.AddrFormatError, IndexError, ValueError):
            pass

        for hint, cls in self.type_hints.items():
            if _hint_match(hint, query):
                yield from database.find(keys=query, classes=(cls,))
                return

        yield from database.find(keys=query, classes=classes)

    def query_network(self, net, classes=None, exact_match=False,
                      database=None):
        database = self._get_database(database)

        if classes is None:
            classes = self.network_classes
        else:
            classes = set(classes).intersection(self.network_classes)

        inetnum_classes = self.filter_classes(classes, self.cidr_classes,
                                              database=database)
        route_classes = self.filter_classes(classes, self.route_classes,
                                            database=database)
        address_classes = self.filter_classes(classes, self.address_classes,
                                              database=database)

        if not isinstance(net, netaddr.IPNetwork):
            net = netaddr.IPNetwork(net)
        supernets = {str(n) for n in net.supernet()} | {str(net)}

        addresses = database.find(classes=address_classes, keys=(str(net.ip),))
        if exact_match:
            inetnums = database.lookup(classes=inetnum_classes, keys=(str(net),))
        else:
            inetnums = database.lookup(classes=inetnum_classes, keys=supernets)
        routes = database.lookup(classes=route_classes,
                                 keys=lambda s: s.startswith(tuple(supernets)))
        # routes = database.search(
        #        query={rc: set(supernets) for rc in route_classes},
        #        types=route_classes)

        for address in addresses:
            yield address
        # Sort inetnum objects by prefix length
        inetnums = sorted(list(inetnums),
                          key=lambda s: netaddr.IPNetwork(s[1]).prefixlen,
                          reverse=True)
        if inetnums:
            inetnum = database.fetch(*inetnums[0])
            yield inetnum
        elif exact_match:
            return
        for route_spec in routes:
            route = database.fetch(*route_spec)
            if net in route.ip_network:
                yield route

    def query_inverse(self, obj, database=None):
        database = self._get_database(database)
        schema = None
        if self.use_schemas:
            try:
                schema = self._load_schema(obj.type)
            except KeyError:
                pass
        if schema is not None:
            inverse_objects = set()
            for key, _, _, inverse in schema.schema_keys():
                if "nic-hdl" in inverse:
                    inverse.extend(self.handle_classes)
                if "nic-cidr" in inverse:
                    inverse.extend(self.cidr_classes)
                if "nic-addr" in inverse:
                    inverse.extend(self.address_classes)
                if "nic-route" in inverse:
                    inverse.extend(self.route_classes)
                if "nic-net" in inverse:
                    inverse.extend(self.network_classes)
                for value in obj.get(key):
                    for inv in inverse:
                        inverse_objects.add((inv, value))
            for object_class, object_type in sorted(inverse_objects):
                obj = database.try_fetch(object_class, object_type)
                if obj:
                    yield obj
            return

        # Use default rules
        inverse_objects = set()
        inverse_objects.update(obj.get("admin-c"))
        inverse_objects.update(obj.get("tech-c"))
        inverse_objects.update(obj.get("zone-c"))
        inverse_objects.update(obj.get("org"))
        for inverse in inverse_objects:
            yield from database.find(classes=self.handle_classes,
                                     keys=(inverse,))

    def query_abuse(self, obj, database=None):
        database = self._get_database(database)
        if obj.object_class not in self.abuse_classes:
            return
        abuse_contact_key = None
        if "abuse-c" in obj:
            abuse_contact_key = obj["abuse-c"]
        elif "org" in obj:
            org = database.try_fetch("organisation", obj["org"])
            if not org:
                return
            if "abuse-c" in org:
                abuse_contact_key = org["abuse-c"]
            elif "abuse-mailbox" in org:
                return org["abuse-mailbox"]
        if not abuse_contact_key:
            return
        try:
            abuse_contact = next(database.find(classes=self.handle_classes,
                                               keys=abuse_contact_key))
        except StopIteration:
            return
        if not abuse_contact:
            return
        if "abuse-mailbox" in abuse_contact:
            return abuse_contact["abuse-mailbox"]

    def query_reverse_domains(self, term, classes=None, database=None):
        if database is None:
            database = self.new_query_database()
        classes = self.filter_classes(classes)
        domain_class = database.primary_class("domain")
        if domain_class not in classes:
            return
        try:
            net = netaddr.IPNetwork(term)
        except netaddr.core.AddrFormatError:
            return
        for subnet, domain in lglass.dns.rdns_subnets(net):
            try:
                yield database.fetch(domain_class, domain)
            except KeyError:
                pass

    def query_more_specifics(self, obj_or_net, levels=1, database=None):
        if database is None:
            database = self.new_query_database()
        if isinstance(obj_or_net, lglass.object.Object):
            if obj_or_net.type not in self.cidr_classes:
                return
            classes = {obj_or_net.type} | self.address_classes
            net = obj_or_net.ip_network
        else:
            classes = self.address_classes | self.cidr_classes
            net = obj_or_net
        res = set()
        for rel in database.find(classes=classes):
            if rel.ip_network in net:
                res.add(rel)
        yield from sorted(res, key=lambda o: o.ip_network)

    def query_less_specifics(self, obj, levels=1, database=None):
        if database is None:
            database = self.new_query_database()
        if obj.type not in self.cidr_classes:
            return
        found = 0
        for supernet in obj.ip_network.supernet()[::-1]:
            try:
                res = database.fetch(obj.type, str(supernet))
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


default_engine = WhoisEngine()

query = default_engine.query
query_search_inverse = default_engine.query_search_inverse
query_primary = default_engine.query_primary
query_network = default_engine.query_network
query_inverse = default_engine.query_inverse
query_abuse = default_engine.query_abuse
query_reverse_domain = default_engine.query_reverse_domains
query_more_specifics = default_engine.query_more_specifics
query_less_specifics = default_engine.query_less_specifics


def new_argparser(cls=argparse.ArgumentParser, *args, **kwargs):
    if not isinstance(cls, type):
        argparser = cls
    else:
        argparser = cls(*args, **kwargs)
    argparser.add_argument(
        "--domains",
        "-d",
        action="store_true",
        default=False,
        help="return DNS reverse delegation objects too")
    argparser.add_argument("--types", "-T",
                           help="only look for objects of TYPE")
    argparser.add_argument("--one-more", "-m", action="store_const",
                           const=1, dest="more_specific_levels", default=0,
                           help="find all one level more specific matches")
    argparser.add_argument("--all-more", "-M", action="store_const",
                           const=-1, dest="more_specific_levels",
                           help="find all levels of more specific matches")
    argparser.add_argument("--one-less", "-l", action="store_const",
                           const=1, dest="less_specific_levels", default=0,
                           help="find the one level less specific match")
    argparser.add_argument("--all-less", "-L", action="store_const",
                           const=-1, dest="less_specific_levels",
                           help="find all levels less specific matches")
    argparser.add_argument("--exact", "-x", action="store_true",
                           default=False, help="exact match")
    argparser.add_argument(
        "--no-recurse",
        "-r",
        action="store_true",
        default=False,
        help="turn off recursive look-ups for contact information")
    argparser.add_argument(
        "--primary-keys",
        "-K",
        action="store_true",
        default=False,
        help="only primary keys are returned")
    argparser.add_argument("terms", nargs="*")
    return argparser


def args_to_query_kwargs(args):
    kwargs = dict(
        reverse_domain=args.domains,
        less_specific_levels=args.less_specific_levels,
        more_specific_levels=args.more_specific_levels,
        exact_match=args.exact,
        recursive=not args.no_recurse)
    if args.types is not None:
        kwargs["classes"] = args.types.split(",")
    if args.primary_keys:
        kwargs["recursive"] = False
    return kwargs


def main(args=None, stdout=sys.stdout, database_cls=lglass.nic.FileDatabase):
    import argparse
    import time

    if args is None:
        args = sys.argv[1:]

    argparser = new_argparser(description="Perform whois lookups directly")
    argparser.add_argument("--database", "-D", help="Path to database",
                           default=".")
    argparser.add_argument("-q")
    argparser.add_argument("--inverse", "-i")

    args = argparser.parse_args()

    db = database_cls(args.database)
    eng = WhoisEngine(db)
    eng.ipv4_more_specific_prefixlens = set(range(0, 33))
    eng.ipv6_more_specific_prefixlens = set(range(0, 129))
    eng.use_schemas = True

    query_kwargs = args_to_query_kwargs(args)

    pretty_print_options = dict(
        min_padding=16,
        add_padding=0)

    if args.q == "types":
        print("\n".join(db.object_classes))
        return

    inverse_fields = None
    if args.inverse is not None:
        inverse_fields = args.inverse.split(",")

    start_time = time.time()
    for term in args.terms:
        print("% Results for query '{query}'".format(query=term))
        print()
        if inverse_fields is not None:
            term = {f: term for f in inverse_fields}
        results = eng.query(term, **query_kwargs)
        for primary in sorted(results.keys(), key=lambda k: k.type):
            primary_key = db.primary_key(primary)
            related_objects = list(results[primary])[1:]
            abuse_contact = eng.query_abuse(primary)
            if abuse_contact:
                print("% Abuse contact for '{}' is '{}'".format(primary_key,
                                                                abuse_contact))
                print()
            if args.primary_keys:
                primary = primary.primary_key_object()
                print("".join(primary.pretty_print(**pretty_print_options)))
                continue
            print("% Information related to '{}'".format(primary_key))
            print()
            print("".join(primary.pretty_print(**pretty_print_options)))
            for obj in related_objects:
                print("".join(obj.pretty_print(**pretty_print_options)))
    print("% Query took {} seconds".format(time.time() - start_time),
          file=stdout)


if __name__ == "__main__":
    import cProfile
    main()
