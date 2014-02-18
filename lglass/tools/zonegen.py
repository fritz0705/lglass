# coding: utf-8

import sys
import argparse

import netaddr

import lglass.generators.dns
import lglass.database.backends

def build_argparser():
	argparser = argparse.ArgumentParser(description="Generator for delegating zones")
	argparser.add_argument("--database", "--db", "-d", help="Whois database",
			type=str, default=".")
	argparser.add_argument("--nameserver", "-n", dest="nameservers", action="append",
			help="Nameserver")
	argparser.add_argument("--master", "-m", help="Master nameserver")
	argparser.add_argument("--email", "-e", help="Email address for SOA",
			required=True)
	argparser.add_argument("--ttl", "-t", help="Time to live for generated zone",
			type=int, default=3600)

	subparsers = argparser.add_subparsers(dest='type')

	argparser_dns = subparsers.add_parser('dns')
	argparser_rdns4 = subparsers.add_parser('rdns4')
	argparser_rdns6 = subparsers.add_parser('rdns6')

	argparser_dns.add_argument('--zone', '-z', help="DNS Zone", required=True)
	argparser_rdns4.add_argument("--network", "-N", help="IPv4 Network")
	argparser_rdns6.add_argument("--network", "-N", help="IPv6 Network")

	return argparser

def main(argv=sys.argv[1:]):
	argparser = build_argparser()
	args = argparser.parse_args(argv)

	backend = lglass.database.backends.FileSystemBackend(args.database)
	master_nameserver = args.master
	if master_nameserver is None:
		if args.nameservers:
			master_nameserver = args.nameservers[0]
		else:
			master_nameserver = args.zone
	args.master = master_nameserver

	if args.type == "dns":
		return main_dns(args, backend)
	elif args.type == "rdns4":
		return main_rdns4(args, backend)
	elif args.type == "rdns6":
		return main_rdns6(args, backend)

def main_dns(args, backend):
	domains = (backend.get_object(*spec) for spec in backend.list_all_objects()
		if (spec[0] == "dns" or spec[0] == "domain")
		and spec[1].endswith("." + args.zone))

	soa = lglass.generators.dns.generate_soa(args.zone,
		args.master,
		args.email)

	zone = ["$TTL {time}".format(time=args.ttl)]

	zone.extend(lglass.generators.dns.generate_zone(
		args.zone,
		domains,
		soa=soa,
		nameservers=args.nameservers
	))

	print("\n".join(map(str, zone)))

def main_rdns4(args, backend):
	inetnums = (backend.get_object("inetnum", spec) for spec in backend.list_objects("inetnum"))

	network = netaddr.IPNetwork(args.network)
	zone = lglass.generators.dns.rdns_domain(network)

	soa = lglass.generators.dns.generate_soa(zone, args.master, args.email)

	zone = ["$TTL {time}".format(time=args.ttl)]

	zone.extend(lglass.generators.dns.generate_rdns4_zone(
		network=network,
		inetnums=inetnums,
		soa=soa,
		nameservers=args.nameservers
	))

	print("\n".join(map(str, zone)))

def main_rdns6(args, backend):
	inet6nums = (backend.get_object("inet6num", spec) for spec in backend.list_objects("inet6num"))

	network = netaddr.IPNetwork(args.network)
	zone = lglass.generators.dns.rdns_domain(network)

	soa = lglass.generators.dns.generate_soa(zone, args.master, args.email)

	zone = ["$TTL {time}".format(time=args.ttl)]

	zone.extend(lglass.generators.dns.generate_rdns6_zone(
		network,
		inet6nums,
		soa=soa,
		nameservers=args.nameservers
	))

	print("\n".join(map(str, zone)))

if __name__ == "__main__":
	main()

