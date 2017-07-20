# coding: utf-8

import netaddr

def rdns_domain(network):
    """Transform :py:class:`netaddr.IPNetwork` object to rDNS zone name"""
    if network.prefixlen == 0:
        return "ip6.arpa" if network.version == 6 else "in-addr.arpa"
    if network.version == 4:
        return ".".join(map(str, reversed(network.ip.words[:network.prefixlen // 8]))) + ".in-addr.arpa"
    elif network.version == 6:
        return ".".join(map(str, reversed(list("".join(hex(n)[2:].rjust(4, "0") for n in network.ip.words))[:network.prefixlen // 4]))) + ".ip6.arpa"

def rdns_subnets(network):
    next_prefixlen = 8 * ((network.prefixlen - 1) // 8 + 1) if network.version == 4 else 4 * ((network.prefixlen - 1) // 4 +1)
    for subnet in network.subnet(next_prefixlen):
        yield (subnet, rdns_domain(subnet))

def rdns_network(domain):
    if domain.endswith(".ip6.arpa"):
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
    elif domain.endswith(".in-addr.arpa"):
        domain = domain[:-13]
        prefixlen = (domain.count(".") + 1) * 8
        network = ""
        for octet in domain.split(".")[::-1]:
            network += octet + "."
        network += "0." * ((32 - prefixlen) //8)
        if network[-1] == '.': network = network[:-1]
        return netaddr.IPNetwork(network + "/{}".format(prefixlen))
    elif domain == "ip6.arpa":
        return netaddr.IPNetwork("::/0")
    elif domain == "in-addr.arpa":
        return netaddr.IPNetwork("0.0.0.0/0")

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
    return "{domain}. IN DS {rrdata}".format(domain=domain, rrdata=rrdata)

def generate_delegation(domain, comments=False, include_glue=True, include_ds=True):
    if comments:
        yield "; {domain} ZONE-C {zonec} ADMIN-C {adminc} TECH-C {techc}".format(
                domain=domain["domain"],
                zonec=",".join(domain.get("zone-c")) or "(unknown)",
                adminc=",".join(domain.get("admin-c")) or "(unknown)",
                techc=",".join(domain.get("tech-c")) or "(unknown)")
    for nserver_record in domain.get("nserver"):
        server, *glues = nserver_record.split()
        yield ns_delegation(domain["domain"], server)
        if glues and server.endswith("." + domain["domain"]) and include_glue:
            for glue in glues:
                yield glue_record(server, glue)
    if include_ds:
        for ds_rrdata in domain.get("ds-rrdata"):
            yield ds_delegation(domain["domain"], ds_rrdata)

def generate_delegations(domains, **kwargs):
    for domain in domains:
        yield from generate_delegation(domain, **kwargs)

if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser(description="Generator for NIC domain zones")
    argparser.add_argument("--database", "-D", help="Path to database", default=".")
    argparser.add_argument("--comments", help="Enable comments", dest="include_comments", default=False, action="store_true")
    argparser.add_argument("--no-comments", help="Disable comments", dest="include_comments", action="store_false")
    argparser.add_argument("--base", help="Enable base zone information", action='store_true', dest='include_base', default=True)
    argparser.add_argument("--no-base", help="Disable base zone information", action='store_false', dest='include_base')
    argparser.add_argument("--glue", help="Include glue records in generated RRs", action="store_true", dest="include_glue", default=True)
    argparser.add_argument("--no-glue", help="Do not include glue records in generated RRs", action="store_false", dest="include_glue")
    argparser.add_argument("--dnssec", help="Include DS records in generated RRs", action="store_true", dest="include_ds", default=True)
    argparser.add_argument("--no-dnssec", help="Do not include DS records in generated RRs", action="store_false", dest="include_ds")
    argparser.add_argument("--dn42", help="Enable DN42 mode", action="store_true", default=False)
    argparser.add_argument("zone", help="Base domain name")

    args = argparser.parse_args()

    if args.dn42:
        import lglass.dn42
        db = lglass.dn42.DN42Database(args.database)
    else:
        import lglass.database
        db = lglass.database.SimpleDatabase(args.database)

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

    domains = set(db.lookup(types="domain"))
    for _, domain_name in domains:
        if (not domain_name.endswith("." + args.zone) and args.zone) or domain_name == args.zone:
            continue
        try:
            domain = db.fetch("domain", domain_name)
            print("\n".join(generate_delegation(domain, **gendel_kwargs)))
        except KeyError:
            print("; {} NOT FOUND".format(domain_name))
        except Exception as r:
            raise Exception(domain_name, r)

