# coding: utf-8

import sys
import argparse
import json

import lglass.route
import lglass.bird

def main(args=sys.argv[1:]):
	argparser = argparse.ArgumentParser()
	argparser.add_argument("-4", dest="birdc", action="store_const", const="birdc")
	argparser.add_argument("-6", dest="birdc", action="store_const", const="birdc6")
	argparser.add_argument("-b", "--birdc", default="birdc", help="Path to birdc executable")

	argparser.add_argument("-t", "--table", help="Routing table to export")
	argparser.add_argument("-p", "--protocol", help="Protocol to export")

	args = argparser.parse_args(args)

	client = lglass.bird.BirdClient(args.birdc)
	query = {}
	if args.table:
		query["table"] = args.table
	if args.protocol:
		query["protocol"] = args.protocol
	routes = client.routes(**query)
	routes = lglass.route.RoutingTable(routes)

	if sys.stdout.isatty():
		print(routes.to_json())
	else:
		sys.stdout.raw.write(routes.to_cbor())

if __name__ == "__main__":
	main()

