import re

import netaddr


def roa_entries(obj):
    cidr = netaddr.IPNetwork(obj.key)
    for origin in obj.get("origin"):
        if not re.match(r"AS[0-9]+$", origin):
            continue
        autnum = origin[2:]
        yield (cidr, cidr.prefixlen, int(autnum))


def bird_roa(entry, table=None):
    appendum = ""
    if table:
        appendum = " table {}".format(table)
    return "add roa {prefix} max {max} as {autnum}".format(
        prefix=str(entry[0]),
        max=entry[1],
        autnum=entry[2]) + appendum


if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser(
        description="Generate ROA table from route objects")
    argparser.add_argument("--version", help="IP version", type=int, default=6)
    argparser.add_argument(
        "-4",
        help="IP version 4",
        dest="version",
        action="store_const",
        const=4)
    argparser.add_argument(
        "-6",
        help="IP version 6",
        dest="version",
        action="store_const",
        const=6)
    argparser.add_argument("database", help="Database path", type=str)
    argparser.add_argument("--table", "-t", help="Destination table", type=str)
    argparser.add_argument(
        "--flush",
        "-F",
        help="Flush table before adding entries",
        action="store_true",
        default=False)
    argparser.add_argument(
        "--weak-maxlen",
        "-M",
        help="Do not enforce strict maximum lengths",
        action="store_true",
        default=False)

    args = argparser.parse_args()

    import lglass.dn42
    db = lglass.dn42.DN42Database(args.database)

    if args.version == 4:
        classes = {"route"}
    elif args.version == 6:
        classes = {"route6"}
    else:
        pass

    if args.flush:
        if args.table:
            print("flush roa table {}".format(args.table))
        else:
            print("flush roa")

    for route in db.find(classes=classes):
        for entry in roa_entries(route):
            if args.weak_maxlen:
                entry = list(entry)
                entry[1] = 128 if entry[0].version == 6 else 32
            print(bird_roa(entry, table=args.table))
