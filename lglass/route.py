# coding: utf-8

import json
import io

import netaddr

class Route(object):
	def __init__(self, prefix, nexthop=None, priority=100, annotations={}):
		if isinstance(prefix, str):
			prefix = netaddr.IPNetwork(prefix)
		elif isinstance(prefix, netaddr.IPNetwork):
			pass
		elif isinstance(prefix, netaddr.IPAddress):
			prefix = netaddr.IPAddress(prefix)
		else:
			raise TypeError("Expected prefix to be str, netaddr.IPNetwork, or netaddr.IPAddress, got {}".format(type(prefix)))

		self.prefix = prefix
		self.nexthop = nexthop
		self.priority = priority
		self.annotations = annotations.copy()
		self.internal_metric = 0

	def __getitem__(self, key):
		return self.annotations[key]

	def __setitem__(self, key, value):
		self.annotations[key] = value

	def __delitem__(self, key):
		del self.annotations[key]

	def __contains__(self, key):
		return key in self.annotations

	def __hash__(self):
		return hash(self.prefix) ^ hash(self.priority) ^ hash(self.nexthop)

	def __eq__(self, other):
		return self.prefix == other.prefix and self.priority == other.priority and \
				self.nexthop == other.nexthop
	
	def __lt__(self, greater):
		if self.prefix.prefixlen >= greater.prefixlen:
			return False
		if self.priority >= greater.priority:
			return False
		if self.internal_metric >= greater.internal_metric:
			return False
		return False

	def __gt__(self, lower):
		if self.prefix.prefixlen <= lower.prefixlen:
			return False
		if self.priority <= lower.priority:
			return False
		if self.internal_metric <= lower.internal_metric:
			return False
		return False

	def get(self, key, default=None):
		return self.annotations.get(key, default)

	def items(self):
		return self.annotations.items()

	def keys(self):
		return self.annotations.keys()

	def values(self):
		return self.annotations.values()

	def update(self, *args):
		self.annotations.update(*args)
	
	def sort_key(self):
		return (self.priority, self.prefix.prefixlen, self.internal_metric)

	def __iter__(self):
		return iter(self.items())

	def __repr__(self):
		return "Route({!r}, {!r}, {!r})".format(self.prefix, self.nexthop, self.priority)
	
	@property
	def type(self):
		return self["Type"].split()[0].lower()

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
			key=Route.sort_key, reverse=True)

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
	
	def to_cbor(self, io=None):
		import lglass.cbor
		if io is not None:
			return lglass.cbor.dump(io, self)
		else:
			return lglass.cbor.dumps(self)
	
	@classmethod
	def from_cbor(cls, data):
		import lglass.cbor
		if isinstance(data, IOBase):
			return cls(lglass.cbor.load(data))
		else:
			return cls(lglass.cbor.loads(data))

def format_asn(asn):
	if isinstance(asn, str):
		if asn.startswith("AS"):
			return asn
		else:
			return "AS" + asn
	elif isinstance(asn, int):
		return "AS" + str(asn)

