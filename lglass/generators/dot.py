# coding: utf-8

import sys

def _spec_id(spec):
	import hashlib
	return "x" + hashlib.md5(":".join(str(spec)).encode()).hexdigest()

def _window(iterable, size=2):
	i = iter(iterable)
	win = []
	for e in range(size):
		win.append(next(i))
	yield win
	for e in i:
		win = win[1:] + [e]
		yield win

def _format_asn(asn):
	if isinstance(asn, str):
		if asn.startswith("AS"):
			return asn
		else:
			return "AS" + asn
	elif isinstance(asn, int):
		return "AS" + str(asn)

def _colors():
	while True:
		for color in [
				"aquamarine",
				"bisque",
				"blue",
				"blueviolet",
				"brown",
				"burlywood",
				"cadetblue",
				"chartreuse",
				"chocolate",
				"coral",
				"cornflowerblue",
				"crimson",
				"cyan",
				"darkgoldenrod",
				"darkgreen",
				"darkorange",
				"darkorchid",
				"darksalmon",
				"deeppink",
				"firebrick"
			]:
			yield color

def routing_graph(rtable, dest, local_address, local_asn):
	routes = rtable.match_all(dest)
	local_asn = _format_asn(local_asn);

	builder = []
	builder.append("digraph {");

	builder.append("{node} [shape=box,label=\"{label}\"];".format(
		node=_spec_id(local_address),
		label=local_address))
	builder.append("{node} [shape=box,label=\"{label}\"];".format(
		node=_spec_id(dest),
		label=dest))
	builder.append("{node} [label=\"{label}\"];".format(
		node=_spec_id(local_asn),
		label=local_asn))

	for color, route in zip(_colors(), routes):
		if not route.type == "bgp":
			continue
		as_path = list(map(int, route["BGP.as_path"].split()))
		if not as_path:
			continue
		builder.append("{left} -> {right} [color={color}];".format(
			left=_spec_id(local_address),
			right=_spec_id(local_asn),
			color=color))
		builder.append("{left} -> {right} [color={color}];".format(
			left=_spec_id(local_asn),
			right=_spec_id(as_path[0]),
			color=color))
		builder.append("{left} -> {right} [color={color}];".format(
			left=_spec_id(as_path[-1]),
			right=_spec_id(dest),
			color=color))
		for as1, as2 in _window(as_path):
			builder.append("{left} -> {right} [color={color}];".format(
				left=_spec_id(as1),
				right=_spec_id(as2),
				color=color))
		for asn in as_path:
			builder.append("{node} [label=\"{label}\"];".format(
				node=_spec_id(asn),
				label="AS{}".format(asn)))

	builder.append("}")
	return "\n".join(builder)

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
	
	builder.extend(peering_graph(rtable, join=False))
	
	builder.append("}")
	return "\n".join(builder)

def peering_graph(rtable, join=True):
	builder = []
	if join:
		builder.append("digraph {")

	peer_info = {}

	for route in rtable:
		if not route["Type"].startswith("BGP"):
			continue
		as_path = map(int, route["BGP.as_path"].split())
		for as1, as2 in _window(as_path):
			if (as1, as2) not in peer_info:
				peer_info[(as1, as2)] = 0
			peer_info[(as1, as2)] += 1

	max_routes = max(peer_info.values())
	min_routes = min(peer_info.values())

	colors = {
		0: "grey50",
		1: "grey45",
		2: "grey40",
		3: "grey35",
		4: "grey30",
		5: "grey25",
		6: "grey20",
		7: "grey15",
		8: "grey10",
		9: "grey5",
		10: "grey0"
	}

	for peering, routes in peer_info.items():
		color = colors[int((routes - min_routes) / (max_routes - min_routes) * 10)]
		builder.append("AS{left} -> AS{right} [color={color}];".format(
			left=peering[0], right=peering[1], color=color))
	
	if join:
		builder.append("}")
		return "\n".join(builder)
	else:
		return builder

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
		with open(_rt, "rb") as fh:
			rtable.update(lglass.route.RoutingTable.from_data(fh, args.format))
	
	print(network_graph(rtable))

def main_peering(args):
	import lglass.route

	rtable = lglass.route.RoutingTable()

	for _rt in args.rtables:
		with open(_rt, "rb") as fh:
			rtable.update(lglass.route.RoutingTable.from_data(fh, args.format))
	
	print(peering_graph(rtable))

def main_routing(args):
	import lglass.route

	rtable = lglass.route.RoutingTable()

	for _rt in args.rtables:
		with open(_rt, "rb") as fh:
			rtable.update(lglass.route.RoutingTable.from_data(fh, args.format))
	
	print(routing_graph(rtable, args.destination, args.local_ip, args.local_as))

def main(args=sys.argv[1:]):
	import argparse

	import lglass.database.file

	argparser = argparse.ArgumentParser()

	subparsers = argparser.add_subparsers(dest="command")
	
	argparser_db = subparsers.add_parser("database")
	argparser_peerings = subparsers.add_parser("peering")
	argparser_network = subparsers.add_parser("network")
	argparser_routing = subparsers.add_parser("routing")
	subparsers.add_parser("help")

	argparser_db.add_argument("-d", "--database", default=".")
	argparser_db.add_argument("objects", nargs="*")

	argparser_peerings.add_argument("-f", "--format", choices=["cbor", "json"], default="json")
	argparser_peerings.add_argument("rtables", nargs="+")

	argparser_network.add_argument("-f", "--format", choices=["cbor", "json"], default="json")
	argparser_network.add_argument("rtables", nargs="+")

	argparser_routing.add_argument("-f", "--format", choices=["cbor", "json"], default="json")
	argparser_routing.add_argument("destination")
	argparser_routing.add_argument("local_ip")
	argparser_routing.add_argument("local_as")
	argparser_routing.add_argument("rtables", nargs="+")

	args = argparser.parse_args(args)

	_cmd = {
		"database": main_database,
		"peering": main_peering,
		"network": main_network,
		"routing": main_routing
	}.get(args.command, lambda _args: argparser.print_help())(args)

if __name__ == "__main__":
	main()

