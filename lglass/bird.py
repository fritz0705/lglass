# coding: utf-8

import netaddr
import subprocess

class Route:
	def __init__(self, network):
		self.network = netaddr.IPNetwork(network)

	def __repr__(self):
		return "Route({0})".format(repr(self.network))

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

class Parser:
	def __init__(self, static_route=Route, bgp_route=BGPRoute):
		self.static_route = static_route
		self.bgp_route = bgp_route
		pass

	def parse_route_body(self, network, route_body):
		raw_routes = []
		c_route = None
		for key, value in map(lambda x: x.split(": "), route_body):
			if key == "Type":
				if c_route:
					raw_routes.append(c_route)
					c_route = None
				c_route = {}
			c_route[key] = value
		if c_route:
			raw_routes.append(c_route)

		routes = []
		for route in raw_routes:
			if route["Type"].split(" ")[0] == "BGP":
				as_path = route.get("BGP.as_path").split(" ")
				as_path = filter(lambda x: x.isnumeric(), as_path)

				new_route = self.bgp_route(
					network,
					origin=route.get("BGP.origin"),
					as_path=as_path,
					next_hop=route.get("BGP.next_hop"),
					med=route.get("BGP.med"),
				)
				if "BGP.community" in route:
					new_route.community = list(map(lambda x: (int(x[0]), int(x[1])), map(lambda x: x[1:-1].split(","), route.get("BGP.community", "").split(" "))))

			else:
				new_route = self.static_route(network)
			
			routes.append(new_route)

		return routes

	def parse_routes(self, routes):
		network = None
		networks = {}
		for line in routes.split("\n"):
			if len(line) == 0:
				continue
			if line[0] == "\t":
				networks[network].append(line[1:])
			elif line[0:8] == " " * 8:
				networks[network][-1] += "\n" + line.replace(" " * 8, "\t")
			else:
				network = line.split("  ")[0]
				networks[network] = []

		routes = []
		for network, route_body in networks.items():
			routes += self.parse_route_body(network, route_body)

		return routes
	
	def parse_protocols(self, protocols):
		pass
 
class Bird:
	def __init__(self, birdc="birdc", parser=None, default_table=None):
		if parser is None:
			parser = Parser()

		self.default_table = default_table
		self.parser = parser
		self.birdc = birdc

	def get_routes(self, selector=None, table=None, protocol=None, primary=False):
		if table is None:
			table = self.default_table

		query = [ self.birdc, "show", "route" ]
		if selector is not None:
			query.append("for")
			query.append(str(selector))

		if table is not None:
			query.append("table")
			query.append(str(table))

		if protocol is not None:
			query.append("protocol")
			query.append(str(protocol))

		if primary:
			query.append("primary")

		query.append("all")

		proc = subprocess.Popen(query, stdout=subprocess.PIPE)
		data = proc.stdout.read().decode()
		proc.wait()

		return self.parser.parse_routes(data)

