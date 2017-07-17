# coding: utf-8

import netaddr

def rdns_domain(network):
    """Transform :py:class:`netaddr.IPNetwork` object to rDNS zone name"""
    if network.version == 4:
        return ".".join(map(str, reversed(network.ip.words[:network.prefixlen // 8]))) + ".in-addr.arpa"
    elif network.version == 6:
        return ".".join(map(str, reversed(list("".join(hex(n)[2:].rjust(4, "0") for n in network.ip.words))[:network.prefixlen // 4]))) + ".ip6.arpa"

def rdns_network(domain):
    if domain.endswith("ip6.arpa"):
        domain = domain[:-9]
        prefixlen = (domain.count(".") + 1) * 4

        nibbles = domain.split(".")[::-1]
        while len(nibbles) < 32:
            nibbles.append("0")

        network = ""
        nibbles_iter = iter(nibbles)
        try:
            while True:
                n1, n2, n3, n4 = [next(nibbles_iter) for _ in range(4)]
                if n1 is None:
                    break
                network += n1 + n2 + n3 + n4 + ":"
        except StopIteration:
            pass
        return netaddr.IPNetwork(network[:-1] + "/{}".format(prefixlen))
    elif domain.endswith("in-addr.arpa"):
        domain = domain[:-13]
        prefixlen = (domain.count(".") + 1) * 8
        network = ""
        for octet in domain.split(".")[::-1]:
            network += octet + "."
        network += "0." * ((32 - prefixlen) //8)
        if network[-1] == '.': network = network[:-1]
        return netaddr.IPNetwork(network + "/{}".format(prefixlen))

def canonicalize_name(name):
    if name[-1] == '.':
        name = name[:-1]
    return name

def glue_record(domain, glue):
    domain = canonicalize_name(domain)
    if ":" in glue:
        return "{domain}. IN AAAA {glue}".format(domain=domain, glue=glue)
    return "{domain}. IN A {glue}".format(domain=domain, glue=glue)

def ns_delegation(domain, nserver):
    domain = canonicalize_name(domain)
    nserver = canonicalize_name(nserver)
    # TODO sanitize nserver
    return "{domain}. IN NS {nserver}.".format(domain=domain, nserver=nserver)

def ds_delegation(domain, rrdata):
    domain = canonicalize_name(domain)
    # TODO sanitize rrdata
    return "{domain}. IN DS {rrdata}.".format(domain=domain, rrdata=rrdata)

def generate_delegation(domain, comments=False):
    if comments:
        yield "; {domain} ZONE-C {zonec} ADMIN-C {adminc} TECH-C {techc}".format(
                domain=domain["domain"],
                zonec=",".join(domain.get("zone-c")) or "(unknown)",
                adminc=",".join(domain.get("admin-c")) or "(unknown)",
                techc=",".join(domain.get("tech-c")) or "(unknown)")
    for nserver_record in domain.get("nserver"):
        server, *glues = nserver_record.split()
        yield ns_delegation(domain["domain"], server)
        if glues and server.endswith(domain["domain"]):
            for glue in glues:
                yield glue_record(server, glue)
    for ds_rrdata in domain.get("ds-rrdata"):
        yield ds_delegation(domain["domain"], ds_rrdata)

def generate_delegations(domains, comments=False):
    for domain in domains:
        yield from generate_delegation(domain, comments=comments)

if __name__ == "__main__":
    import argparse
    import sys

    argparser = argparse.ArgumentParser(description="Generator for NIC domain zones")
    argparser.add_argument("--database", "-D", help="Path to database", default=".")
    argparser.add_argument("--comments", help="Enable comments", dest="include_comments", default=False, action="store_true")
    argparser.add_argument("--no-comments", help="Disable comments", dest="include_comments", default=False, action="store_false")
    argparser.add_argument("--base", help="Enable base zone information", action='store_true', dest='include_base', default=True)
    argparser.add_argument("--no-base", help="Disable base zone information", action='store_false', dest='include_base')
    argparser.add_argument("--dn42", help="Enable or disable DN42 mode", type=bool, default=False)
    argparser.add_argument("zone", help="Base domain name")

    args = argparser.parse_args()

    if args.dn42:
        import lglass.dn42
        db = lglass.dn42.DN42Database(args.database)
    else:
        import lglass.database
        db = lglass.database.SimpleDatabase(args.database)

    # Fetch primary domain object
    if args.include_base:
        try:
            domain = db.fetch("domain", args.zone)
            print("\n".join(generate_delegation(domain, comments=args.include_comments)))
        except KeyError:
            pass

    domains = set(db.lookup(types="domain"))
    for _, domain_name in domains:
        if not domain_name.endswith("." + args.zone) or domain_name == args.zone:
            continue
        try:
            domain = db.fetch("domain", domain_name)
            print("\n".join(generate_delegation(domain, comments=args.include_comments)))
        except KeyError:
            print("; {} NOT FOUND".format(domain_name))
        except Exception as r:
            raise Exception(domain_name, r)

