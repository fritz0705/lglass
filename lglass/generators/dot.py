# coding: utf-8

import sys

def _window(iterable, size=2):
	i = iter(iterable)
	win = []
	for e in range(size):
		win.append(next(i))
	yield win
	for e in i:
		win = win[1:] + [e]
		yield win

def network_graph(rtable):
	def _spec_id(spec):
		import hashlib
		return "x" + hashlib.md5(":".join(str(spec)).encode()).hexdigest()

	network_announcements = {}

	for route in rtable:
		if not route["Type"].startswith("BGP"):
			continue
		as_path = list(map(int, route["BGP.as_path"].split()))
		if not as_path:
			continue
		if as_path[-1] not in network_announcements:
			network_announcements[as_path[-1]] = set()
		network_announcements[as_path[-1]].add(route.prefix)
	
	builder = []
	builder.append("digraph {")

	for asn, prefixes in network_announcements.items():
		for prefix in prefixes:
			_prefix = _spec_id(prefix)
			builder.append("{pref} -> AS{asn} [arrowhead=none, color=chocolate4];".format(
				pref=_prefix, asn=asn))
			builder.append("{pref} [label=\"{label}\"];".format(
				pref=_prefix, label=str(prefix)))

	seen = set()
	
	for route in rtable:
		if route["Type"].startswith("BGP"):
			as_path = map(int, route["BGP.as_path"].split())
			for as1, as2 in _window(as_path):
				if (as1, as2) in seen or as1 == as2:
					continue
				builder.append("AS{left} -> AS{right};".format(
					left=as1, right=as2))
				seen.add((as1, as2))
	
	builder.append("}")
	return "\n".join(builder)

def peering_graph(rtable):
	builder = []
	builder.append("digraph {")

	seen = set()
	
	for route in rtable:
		if route["Type"].startswith("BGP"):
			as_path = map(int, route["BGP.as_path"].split())
			for as1, as2 in _window(as_path):
				if (as1, as2) in seen or as1 == as2:
					continue
				builder.append("AS{left} -> AS{right};".format(
					left=as1, right=as2))
				seen.add((as1, as2))
	
	builder.append("}")
	return "\n".join(builder)

def database_graph(database, subset=None):
	def _spec_id(spec):
		import hashlib
		return "x" + hashlib.md5(":".join(spec).encode()).hexdigest()

	edges = set()
	nodes = set()

	if subset is not None:
		if isinstance(subset, tuple):
			nodes.add(database.get(*subset))
		elif isinstance(subset, list):
			for elem in subset:
				if isinstance(elem, tuple):
					nodes.add(database.get(*elem))
				else:
					nodes.add(elem)
	else:
		nodes.update(map(lambda l: database.get(*l), database.list()))
	while True:
		new_nodes = set()
		for node in nodes:
			for inverse in node.inverses(database):
				edges.add((node.spec, inverse.spec))
				new_nodes.add(inverse)
		if new_nodes <= nodes:
			break
		nodes.update(new_nodes)

	builder = []
	builder.append("digraph {")

	for node in nodes:
		builder.append("{id} [label=\"{label}\"];".format(
			id=_spec_id(node.spec),
			label=": ".join(node.spec)))
	
	for edge in edges:
		builder.append("{left} -> {right};".format(left=_spec_id(edge[0]),
			right=_spec_id(edge[1])))
	
	builder.append("}")
	
	return "\n".join(builder)

def main_database(args):
	import lglass.database.file

	db = lglass.database.file.FileDatabase(args.database)

	subset_objs = []

	obj_iter = iter(args.objects)
	try:
		for first in obj_iter:
			second = next(obj_iter)
			subset_objs.append(db.get(first, second))
	except StopIteration:
		pass
	
	if subset_objs:
		print(database_graph(db, subset_objs))
	else:
		print(database_graph(db))

def main_network(args):
	import lglass.route

	rtable = lglass.route.RoutingTable()

	for _rt in args.rtables:
		with open(_rt) as fh:
			rtable.update(lglass.route.RoutingTable.from_json(fh.read()))
	
	print(network_graph(rtable))

def main_peering(args):
	import lglass.route

	rtable = lglass.route.RoutingTable()

	for _rt in args.rtables:
		with open(_rt) as fh:
			rtable.update(lglass.route.RoutingTable.from_json(fh.read()))
	
	print(peering_graph(rtable))

def main(args=sys.argv[1:]):
	import argparse

	import lglass.database.file

	argparser = argparse.ArgumentParser()

	subparsers = argparser.add_subparsers(dest="command")
	
	argparser_db = subparsers.add_parser("database")
	argparser_peerings = subparsers.add_parser("peering")
	argparser_network = subparsers.add_parser("network")
	subparsers.add_parser("help")

	argparser_db.add_argument("-d", "--database", default=".")
	argparser_db.add_argument("objects", nargs="*")

	argparser_peerings.add_argument("rtables", nargs="+")

	argparser_network.add_argument("rtables", nargs="+")

	args = argparser.parse_args(args)

	_cmd = {
		"database": main_database,
		"peering": main_peering,
		"network": main_network
	}.get(args.command, lambda _args: argparser.print_help())(args)

if __name__ == "__main__":
	main()

