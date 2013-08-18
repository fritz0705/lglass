# coding: utf-8

import lglass.rpsl
import lglass.database.base

import netaddr

class CIDRDatabase(lglass.database.base.Database):
	""" Extended database type which is a layer between the user and another
	database. It performs CIDR matching and AS range matching on find calls. """
	# TODO reimplement this using a trie

	range_types = {"as-block"}
	cidr_types = {"inetnum", "inet6num", "route", "route6"}

	perform_range = True
	perform_cidr = True

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
				if o.spec not in found_objects])
			found_objects = set([obj.spec for obj in objects])

		if self.perform_range:
			objects.extend([o for o in self.find_by_range(primary_key, types)
				if o.spec not in found_objects])
			found_objects = set([obj.spec for obj in objects])

		return objects

	def find_by_cidr(self, primary_key, types=None):
		cidr_types = self.cidr_types
		if types:
			cidr_types = cidr_types & set(types)

		try:
			primary_key = netaddr.IPNetwork(primary_key)
		except (ValueError, netaddr.core.AddrFormatError):
			return []
		matches = []

		for obj in self.list():
			if obj[0] not in cidr_types:
				continue
			obj_addr = netaddr.IPNetwork(obj[1])
			if primary_key in obj_addr:
				matches.append((obj_addr.prefixlen, obj))

		matches = sorted(matches, key=lambda o: o[0], reverse=True)
		return [self.get(*m[1]) for m in matches]

	def find_by_range(self, primary_key, types=None):
		range_types = self.range_types
		if types:
			range_types = range_types & set(types)

		try:
			primary_key = int(primary_key.replace("AS", ""))
		except ValueError:
			return []

		matches = []

		for obj in self.list():
			if obj[0] not in range_types:
				continue
			obj_range = tuple([int(x.strip()) for x in obj[1].split("/", 2)])
			if len(obj_range) != 2:
				raise ValueError("Expected obj_range to be 2. Your database might be broken")
			if primary_key >= obj_range[0] and primary_key <= obj_range[1]:
				matches.append(((obj_range[1] - obj_range[0]), obj))

		matches = sorted(matches, key=lambda o: o[0], reverse=True)
		return [self.get(*m[1]) for m in matches]

	def save(self, object):
		self.database.save(object)

	def delete(self, type, primary_key):
		self.database.delete(type, primary_key)

	def list(self):
		return self.database.list()

	def __hash__(self):
		return hash(self.database)
