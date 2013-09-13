# coding: utf-8

import lglass.rpsl
import lglass.database.base
import urllib.parse

import netaddr

@lglass.database.base.register("cidr")
class CIDRDatabase(lglass.database.base.Database):
	""" Extended database type which is a layer between the user and another
	database. It performs CIDR matching and AS range matching on find calls. """
	# TODO reimplement this using a trie

	range_types = {"as-block"}
	cidr_types = {"inetnum", "inet6num", "route", "route6"}

	perform_range = True
	perform_cidr = True

	range_slice = slice(None)
	cidr_slice = slice(None)

	def __init__(self, db, **kwargs):
		self.database = db
		self.__dict__.update(kwargs)

	def get(self, type, primary_key):
		return self.database.get(type, primary_key)

	def find(self, primary_key, types=None):
		objects = []
		found_objects = set([])

		objects.extend([o for o in self.database.find(primary_key, types=types)
			if o.spec not in found_objects])
		found_objects = set([obj.spec for obj in objects])

		if self.perform_cidr:
			objects.extend([o for o in self.find_by_cidr(primary_key, types)
				if o.spec not in found_objects][self.cidr_slice])
			found_objects = set([obj.spec for obj in objects])

		if self.perform_range:
			objects.extend([o for o in self.find_by_range(primary_key, types)
				if o.spec not in found_objects][self.range_slice])
			found_objects = set([obj.spec for obj in objects])

		return objects

	def find_by_cidr(self, primary_key, types=None):
		cidr_types = self.cidr_types
		if types:
			cidr_types = cidr_types & set(types)

		try:
			address = netaddr.IPNetwork(primary_key)
		except (ValueError, netaddr.core.AddrFormatError):
			return []

		objects = []

		for supernet in address.supernet():
			supernets = self.database.find(str(supernet), types=cidr_types)
			for _supernet in supernets:
				objects.append((supernet.prefixlen, _supernet))

		return (obj[1] for obj in sorted(objects, key=lambda obj: obj[0], reverse=True))

	def find_by_range(self, primary_key, types=None):
		range_types = self.range_types
		if types:
			range_types = range_types & set(types)

		try:
			primary_key = int(primary_key.replace("AS", ""))
		except ValueError:
			return []

		objects = []

		for type, _primary_key in self.list():
			if type not in range_types:
				continue
			obj_range = tuple([int(x.strip()) for x in _primary_key.split("/", 2)])
			if len(obj_range) != 2:
				continue
			if primary_key >= obj_range[0] and primary_key <= obj_range[1]:
				objects.append((obj_range[1] - obj_range[0], self.get(type, _primary_key)))

		return (obj[1] for obj in sorted(objects, key=lambda obj: obj[0], reverse=True))

	def save(self, object):
		self.database.save(object)

	def delete(self, type, primary_key):
		self.database.delete(type, primary_key)

	def list(self):
		return self.database.list()

	def __hash__(self):
		return hash(self.database)

	@classmethod
	def from_url(cls, url):
		self = cls(None)
		if url.query:
			query = urllib.parse.parse_qs(url.query)
			if "range-types" in query:
				self.range_types = set(query["range-types"][-1].split(","))
			if "cidr-types" in query:
				self.cidr_types = set(query["cidr-types"][-1].split(","))
			if "range-slice" in query:
				self.range_slice = _str_to_slice(query["range-slice"][-1])
			if "cidr-slice" in query:
				self.cidr_slice = _str_to_slice(query["cidr-slice"][-1])
		return self

def _str_to_slice(string):
	if not string:
		return slice(None)
	tokens = []
	for n in string.split(":"):
		try:
			tokens.append(int(n))
		except ValueError:
			tokens.append(None)
	if len(tokens) == 1:
		return slice(*tokens)
	elif len(tokens) == 2:
		return slice(*tokens)
	elif len(tokens) == 3:
		return slice(*tokens)

