# coding: utf-8

import json

import netaddr

class Route(object):
	""" Simple object which holds all relevant routing information """

	def __init__(self, prefix, nexthop=None, metric=100):
		if isinstance(prefix, str):
			prefix = netaddr.IPNetwork(prefix)
		elif isinstance(prefix, netaddr.IPNetwork):
			pass
		elif isinstance(prefix, netaddr.IPAddress):
			prefix = netaddr.IPNetwork(prefix)
		else:
			raise TypeError("Expected prefix to be str, netaddr.IPNetwork, or netaddr.IPAddress, got {}".format(type(prefix)))
		
		self.prefix = prefix
		self.nexthop = nexthop
		self.metric = 100
		self.annotations = {}

	def __getitem__(self, key):
		return self.annotations[key]

	def __setitem__(self, key, value):
		self.annotations[key] = value

	def __delitem__(self, key):
		del self.annotations[key]

	def __contains__(self, key):
		return key in self.annotations

	def __hash__(self):
		return hash(self.prefix) ^ hash(self.nexthop)

	def __repr__(self):
		return "Route({self.prefix!r}, nexthop={self.nexthop!r})".format(self=self)

	def lpm_sort_key(self):
		return (self.prefix.prefixlen, self.metric)

	def to_dict(self):
		return {
			"prefix": str(self.prefix),
			"nexthop": [str(p) for p in self.nexthop] if self.nexthop else None,
			"metric": self.metric,
			"annotations": self.annotations
		}

	def dump(self):
		return self.to_dict()

	@property
	def type(self):
		return self["Type"].split()[0].lower()
	
	@classmethod
	def from_dict(cls, d):
		self = cls(d["prefix"])
		if d["nexthop"]:
			self.nexthop = (netaddr.IPAddress(d["nexthop"][0]), d["nexthop"][1])
		self.annotations = d["annotations"].copy()
		self.metric = d["metric"]
		return self

	load = from_dict

class RoutingTable(object):
	""" Simple collection type, which holds routes and supports longest prefix
	match """

	def __init__(self, iterable=None):
		self.routes = set()
		if iterable is not None:
			self.update(iterable)
	
	def update(self, iterable):
		self.routes.update(iterable)

	def add(self, route):
		if not isinstance(route, Route):
			raise TypeError("Expected route to be a Route, got {}".format(type(route)))
		self.routes.add(route)

	def remove(self, route):
		if not isinstance(route, Route):
			raise TypeError("Expected route to be a Route, got {}".format(type(route)))
		self.routes.remove(route)
	
	def clear(self):
		self.routes.clear()

	def match_all(self, addr):
		if isinstance(addr, str):
			addr = netaddr.IPAddress(addr)
		elif isinstance(addr, netaddr.IPAddress):
			pass
		else:
			raise TypeError("Expected addr to be str or netaddr.IPAddress, got {}".format(type(addr)))

		return sorted((route for route in self if addr in route.prefix),
			key=Route.lpm_sort_key, reverse=True)

	def match(self, addr):
		try:
			return self.match_all(addr)[0]
		except IndexError:
			return None

	def __repr__(self):
		return "RoutingTable({self.routes!r})".format(self=self)

	def __iter__(self):
		return iter(self.routes)

	def __len__(self):
		return len(self.routes)

	def dump(self):
		for route in self.routes:
			yield route.dump()

	def load(self, iterable):
		for route in iterable:
			self.routes.add(Route.load(iterable))

	def to_json(self, fh=None):
		if fh is None:
			return json.dumps(list(self.dump()))
		else:
			return json.dump(list(self.dump()), fh)

	dump_json = to_json

	def to_cbor(self, fh=None):
		import flynn
		if fh is None:
			return flynn.dumps(map(Route.to_dict, self.routes))
		else:
			return flynn.dump(map(Route.to_dict, self.routes), fh)

	dump_cbor = to_cbor

	def load_json(self, data):
		if hasattr(data, "read"):
			routes = json.load(data)
		else:
			routes = json.loads(data)
		for route in routes:
			self.routes.add(Route.from_dict(route))

	def load_cbor(self, data):
		import flynn
		for route in flynn.load(data):
			self.routes.add(Route.from_dict(route))

	@classmethod
	def from_json(cls, data):
		self = cls()
		self.load_json(data)
		return self

	@classmethod
	def from_cbor(cls, data):
		self = cls()
		self.load_cbor(data)
		return self

	@classmethod
	def from_data(cls, data, format):
		if format == "json":
			return cls.from_json(data)
		elif format == "cbor":
			return cls.from_cbor(data)
		else:
			raise ValueError("Invalid serialization format {}".format(format))

def format_asn(asn):
	if isinstance(asn, str):
		if asn.startswith("AS"):
			return asn
		else:
			return "AS" + asn
	elif isinstance(asn, int):
		return "AS" + str(asn)

