#!/usr/bin/env python3

import lglass.generators.dns
import lglass.database

if __name__ == "__main__":
	import argparse

	argparser = argparse.ArgumentParser(description="Delegation-only zone file generator")
	argparser.add_argument("--database", "--db", "-d", help="Whois database",
			type=str, default=".")
	argparser.add_argument("--zone", "-z", help="Zone", required=True)
	argparser.add_argument("--nameserver", "-n", action="append", help="Nameserver")
	argparser.add_argument("--master", "-m", help="Master nameserver")
	argparser.add_argument("--email", "-e", help="Email address of zone maintainer", required=True)
	argparser.add_argument("--ttl", "-t", help="Time to live for generated records"
			type=int, default=3600)

	args = argparser.parse_args()

	db = lglass.database.FileDatabase(args.database)
	domains = (db.get(*spec) for spec in db.list() if spec[0] == "dns" and spec[1].endswith("." + args.zone))

	master_nameserver = args.master
	if master_nameserver is None:
		if args.nameserver:
			master_nameserver = args.nameserver[0]
		else:
			master_nameserver = args.zone
	soa = lglass.generators.dns.generate_soa(args.zone,
		master_nameserver,
		args.email)

	zone = ["$TTL {time}".format(time=args.ttl)]

	zone.extend(lglass.generators.dns.generate_zone(
		args.zone,
		domains,
		soa=soa,
		nameservers=args.nameserver
	))

	print("\n".join(zone))

