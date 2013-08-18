# coding: utf-8

import sys
import argparse

import lglass.generators.roa
import lglass.database.file

def build_argparser():
	argparser = argparse.ArgumentParser(description="Generator for ROA tables")
	argparser.add_argument("--database", "-D", default=".", type=str,
			help="Path to database")
	argparser.add_argument("--table", "-t", default="roa1", type=str,
			help="Name of ROA table")
	argparser.add_argument("--flush", "-f", action="store_true", default=False,
			help="Flush table entries before insertion")
	argparser.add_argument("-6", dest="protocol", action="store_const", const=6,
			help="Generate IPv6 ROA table")
	argparser.add_argument("-4", dest="protocol", action="store_const", const=4,
			help="Generate IPv4 ROA table")

	return argparser

def main(argv=sys.argv[1:]):
	argparser = build_argparser()
	args = argparser.parse_args(argv)

	db = lglass.database.file.FileDatabase(args.database)

	if args.protocol == 4 or args.protocol is None:
		routes = (db.get(*spec) for spec in db.list() if spec[0] == "route")
	elif args.protocol == 6:
		routes = (db.get(*spec) for spec in db.list() if spec[0] == "route6")

	if args.flush:
		print("flush roa table {table}".format(table=args.table))
	
	print("\n".join(lglass.generators.roa.roa_table(routes, args.table)))

if __name__ == "__main__":
	main()

