# coding: utf-8

class Digraph(object):
	""" Digraph is a simple and more or less efficient implementation of a
	directed graph. It aims to provide all necessary methods for digraphs and to
	be simple to understand. Therefore, Digraph isn't efficient in any way. When
	you are looking for an efficient digraph implementation, look at FastDigraph.
	"""
	def __init__(self, data=None):
		self.arcs = set()
		self.arc_weights = {}
		if data is not None:
			self.update(data)

	def add(self, v1, v2, weight=None):
		self.add_arc((v1, v2), weight)

	def add_arc(self, arc, weight=None):
		self.arcs.add(arc)
		self.arc_weights[arc] = weight

	def weight(self, v1, v2, default=None):
		return self.arc_weights.get((v1, v2), default)

	def remove(self, v1, v2):
		self.remove_arc((v1, v2))

	def remove_arc(self, arc):
		self.arcs.remove(arc)

	def neighbors(self, v):
		for v1, v2 in self.arcs:
			if v1 == v:
				yield v2
	
	def adjacent(self, v1, v2):
		return (v1, v2) in self.arcs

	def vertices(self):
		s = set()
		for vs in self.arcs:
			for v in vs:
				if v not in s:
					yield v
					s.add(v)

	def update(self, arcs):
		for t in arcs:
			if len(t) == 3:
				v1, v2, weight = t
			elif len(t) == 2:
				weight = None
				v1, v2 = t
			self.add(v1, v2, weight=weight)
	
	def __iter__(self):
		for v1, v2 in self.arcs:
			yield (v1, v2, self.weight(v1, v2))

	def __contains__(self, arc):
		return arc in self.arcs

	def __hash__(self):
		return hash(self.arcs)

	def __len__(self):
		return len(self.arcs)

	def arcs_dot(self):
		for v1, v2 in self.arcs:
			yield "\"{v1}\" -> \"{v2}\"".format(v1=hash(v1), v2=hash(v2))

	def vertices_dot(self):
		for v in self.vertices():
			yield "\"{v}\" [label=\"{l}\"]".format(v=hash(v), l=str(v))

	def dot(self):
		yield from self.vertices_dot()
		yield from self.arcs_dot()

	def dijkstra(self, src, weight=None):
		if weight is None: weight = self.weight

		# Dijkstra algorithm state
		distance = {}
		previous = {}
		unvisited = set()

		# Define distance from source to source as 0
		distance[src] = 0

		# Define any other distance to infinity and create entry for previous
		# object in hash table
		for vertex in self.vertices():
			if vertex != src:
				distance[vertex] = float("inf")
				previous[vertex] = None
			unvisited.add(vertex)

		while unvisited:
			vertex = sorted(unvisited, key=lambda v: distance[v]).pop(0)
			unvisited.remove(vertex)

			for neighbor in self.neighbors(vertex):
				dist = float(weight(vertex, neighbor, 0))
				alt = distance[vertex] + dist
				if alt < distance[neighbor]:
					distance[neighbor] = alt
					previous[neighbor] = vertex

		return distance, previous

	def dijkstra_path(self, src, dst, weight=None):
		path = []
		dist, prev = self.dijkstra(src, weight=weight)
		while dst in prev:
			path.insert(0, dst)
			dst = prev[dst]
		return path

	def dijkstra_tree(self, src, weight=None):
		if weight is None: weight = self.weight
		dist, prev = self.dijkstra(src, weight=weight)
		g = Digraph()
		for k, v in prev.items():
			g.add(v, k, weight(v, k))
		return g
	
	def subtree(self, src, initial=[]):
		g = Digraph()
		g.handle_neighbors = False
		s = set(initial)
		unvisited = set([src])
		while unvisited:
			v = unvisited.pop()
			s.add(v)
			for n in set(self.neighbors(v)) - s:
				g.add(v, n, self.weight(v, n))
				unvisited.add(n)
		return g

