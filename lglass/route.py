# coding: utf-8

import netaddr

class Route:
	def __init__(self, network):
		self.network = netaddr.IPNetwork(network)

	def __repr__(self):
		return "Route({0})".format(repr(self.network))

	def __str__(self):
		return "{0}\n".format(self.network)
	
	@classmethod
	def type_filter(cls, route):
		return isinstance(route, cls)

class BGPRoute(Route):
	def __init__(self, network, origin="IGP", as_path=[], next_hop=None,
			community=[], med=0):
		Route.__init__(self, network)
		if med is not None:
			med = int(med)
		else:
			med = 0

		as_path = filter(lambda x: x.isnumeric(), as_path)

		self.origin = origin
		self.as_path = list(map(lambda a: int(a), as_path))
		self.next_hop = netaddr.IPAddress(next_hop)
		self.community = list(map(lambda c: (int(c[0]), int(c[1])), community))
		self.med = med

	def as_path_pairs(self):
		pairs = []
		i = 0
		while i < len(self.as_path) - 1:
			pair = (self.as_path[i], self.as_path[i + 1])
			if pair not in pairs and pair[0] != pair[1]:
				pairs.append(pair)
			i += 1
		return pairs

	def __repr__(self):
		return "BGPRoute({network}, origin={origin}, as_path={as_path}, next_hop={next_hop}, community={community}, med={med})".format(
			network=repr(self.network),
			origin=repr(self.origin),
			as_path=repr(self.as_path),
			next_hop=repr(self.next_hop),
			community=repr(self.community),
			med=repr(self.med)
		)
	
	def __str__(self):
		string = Route.__str__(self)

		string += "\tType: BGP unicast univ\n"
		string += "\tBGP.origin: {0}\n".format(self.origin)
		string += "\tBGP.as_path: {0}\n".format(" ".join(map(lambda x: str(x), self.as_path)))
		string += "\tBGP.next_hop: {0}\n".format(self.next_hop)
		string += "\tBGP.med: {0}\n".format(self.med)

		if self.community:
			string += "\tBGP.community: {0}\n".format(" ".join(map(lambda x: "({0[0]},{0[1]})".format(x), self.community)))

		return string
