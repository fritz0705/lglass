# coding: utf-8

import sys

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

def main(args=sys.argv[1:]):
	import argparse

	import lglass.database.file

	argparser = argparse.ArgumentParser()
	argparser.add_argument("-d", "--database", default=".")
	argparser.add_argument("objects", nargs="*")

	args = argparser.parse_args(args)

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

if __name__ == "__main__":
	main()

