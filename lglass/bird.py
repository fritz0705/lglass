# coding: utf-8

import subprocess
from lglass.route import Route, BGPRoute

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
 
class Client:
	def __init__(self, birdc="birdc", parser=None, default_table=None, route_filter=None):
		if parser is None:
			parser = Parser()

		self.route_filter = route_filter
		self.default_table = default_table
		self.parser = parser
		self.birdc = birdc

	def get_routes(self, table=None, primary=False, sort=False):
		if table is None:
			table = self.default_table

		query = [ self.birdc, "show", "route", "table", table ]

		if primary:
			query.append("primary")
		
		query.append("all")

		proc = subprocess.Popen(query, stdout=subprocess.PIPE)
		routes = self.parser.parse_routes(proc.stdout.read().decode())
		proc.wait()

		return list(routes)
	
