# coding: utf-8

from lglass.dns import *

def main(args=None, database_cls=None):
    if database_cls is None:
        import lglass.nic
        database_cls = lglass.nic.FileDatabase
    if args is None:
        import sys
        args = sys.argv[1:]

    import argparse

    argparser = argparse.ArgumentParser(
        description="Generator for NIC domain zones")
    argparser.add_argument(
        "--database",
        "-D",
        help="Path to database",
        default=".")
    argparser.add_argument(
        "--comments",
        help="Enable comments",
        dest="include_comments",
        default=False,
        action="store_true")
    argparser.add_argument(
        "--no-comments",
        help="Disable comments",
        dest="include_comments",
        action="store_false")
    argparser.add_argument(
        "--base",
        help="Enable base zone information",
        action='store_true',
        dest='include_base',
        default=True)
    argparser.add_argument(
        "--no-base",
        help="Disable base zone information",
        action='store_false',
        dest='include_base')
    argparser.add_argument(
        "--glue",
        help="Include glue records in generated RRs",
        action="store_true",
        dest="include_glue",
        default=True)
    argparser.add_argument(
        "--no-glue",
        help="Do not include glue records in generated RRs",
        action="store_false",
        dest="include_glue")
    argparser.add_argument(
        "--dnssec",
        help="Include DS records in generated RRs",
        action="store_true",
        dest="include_ds",
        default=True)
    argparser.add_argument(
        "--no-dnssec",
        help="Do not include DS records in generated RRs",
        action="store_false",
        dest="include_ds")
    argparser.add_argument("zone", help="Base domain name")

    args = argparser.parse_args(args)

    db = database_cls(args.database)

    gendel_kwargs = dict(
        comments=args.include_comments,
        include_glue=args.include_glue,
        include_ds=args.include_ds)

    # Fetch primary domain object
    if args.include_base:
        try:
            domain = db.fetch("domain", args.zone)
            print("\n".join(generate_delegation(domain, **gendel_kwargs)))
        except KeyError:
            pass

    db = db.session()
    if hasattr(db, "lookup_domain"):
        domains = db.lookup_domain(args.zone)
    else:
        domains = set(db.lookup(classes=("domain",)))
    for _, domain_name in sorted(domains, key=lambda x: x[1]):
        if (not domain_name.endswith("." + args.zone) and
                args.zone) or domain_name == args.zone:
            continue
        try:
            domain = db.fetch("domain", domain_name)
            print("\n".join(generate_delegation(domain, **gendel_kwargs)))
        except KeyError:
            print("; {} NOT FOUND".format(domain_name))
        except Exception as r:
            raise Exception(domain_name, r)

import lglass_sql.nic
main(database_cls=lglass_sql.nic.NicDatabase)

