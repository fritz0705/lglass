# coding: utf-8

import os.path

import netaddr

import lglass.rpsl

class Database(object):
	__init__ = None

	get = None
	list = None
	find = None

class FileDatabase(Database):
	""" Simple database type which acts on a structured directory structure,
	where types are represented as directories and objects resp. their primary
	keys as files. """
	root_dir = '.'

	object_types = {"inetnum", "inet6num", "route", "route6", "aut-num",
		"as-block", "dns", "mntner", "person", "route-set"}

	def __init__(self, root_dir='.'):
		self.root_dir = root_dir

	def _path_for(self, type, primary_key):
		return os.path.join(self.root_dir, type, primary_key.replace("/", "_"))

	def get(self, type, primary_key):
		obj = None
		try:
			with open(self._path_for(type, primary_key)) as f:
				obj = lglass.rpsl.Object.from_string(f.read())
		except FileNotFoundError:
			raise KeyError(repr((type, primary_key)))
		return obj

	def list(self):
		objects = []

		for type in os.listdir(self.root_dir):
			if type not in self.object_types:
				continue

			for primary_key in os.listdir(os.path.join(self.root_dir, type)):
				if primary_key[0] == '.': continue
				objects.append((type, primary_key.replace("_", "/")))
		
		return objects

	def find(self, primary_key, types=None):
		if types is None:
			types = self.object_types
		objects = []
		for type in types:
			try:
				objects.append(self.get(type, primary_key))
			except KeyError:
				pass
		return objects

class CachedDatabase(Database):
	""" Simple in-memory cache for any database type. Will cache any object and
	flush it on request. """

	def __init__(self, database):
		self.database = database
		self.cache = {}

	def get(self, type, primary_key):
		cache_key = (type, primary_key)

		if cache_key in self.cache:
			return self.cache[cache_key]

		obj = self.database.get(type, primary_key)
		self.cache[cache_key] = obj

		return obj
	
	def list(self):
		cache_key = "list"

		if cache_key in self.cache:
			return self.cache[cache_key]

		ls = self.database.list()
		self.cache[cache_key] = ls

		return ls

	def find(self, primary_key, types=None):
		cache_key = (types, primary_key)

		if cache_key in self.cache:
			return self.cache[cache_key]

		objs = self.database.find(primary_key, types=types)
		self.cache[cache_key] = objs

		return objs

	def flush(self):
		self.cache = {}

class CIDRDatabase(Database):
	""" Extended database type which is a layer between the user and another
	database. It performs CIDR matching and AS range matching on find calls. """
	# TODO reimplement this using a trie

	range_types = {"as-block"}
	cidr_types = {"inetnum", "inet6num", "route", "route6"}

	def __init__(self, database):
		self.database = database

	def get(self, type, primary_key):
		return self.database.get(type, primary_key)

	def find(self, primary_key, types=None):
		objects = []
		found_objects = set([])

		objects.extend([o for o in self.find_by_cidr(primary_key, types)
			if o.spec not in found_objects])
		found_objects = set([obj.spec for obj in objects])

		objects.extend([o for o in self.find_by_range(primary_key, types)
			if o.spec not in found_objects])
		found_objects = set([obj.spec for obj in objects])

		objects.extend(self.database.find(primary_key, types=types))
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

		return [self.get(*m[1]) for m in sorted(matches, key=lambda o: o[0])]

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

		return [self.get(*m[1]) for m in sorted(matches, key=lambda o: o[0])]

	def list(self):
		return self.database.list()

