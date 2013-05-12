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

	object_types = ["inetnum", "inet6num", "route", "route6", "aut-num",
		"as-block", "dns", "mntner", "person", "route-set"]

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

	def find(self, primary_key):
		objects = []
		for type in self.object_types:
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

	def find(self, primary_key):
		cache_key = (None, primary_key)

		if cache_key in self.cache:
			return self.cache[cache_key]

		objs = self.database.find(primary_key)
		self.cache[cache_key] = objs

		return objs

	def flush(self):
		self.cache = {}

class CIDRDatabase(Database):
	""" Extended database type which is a layer before another database. Performs
	more "complex" CIDR operations on requests like CIDR matching. By default,
	this performs only on requests to inetnums, inet6nums, route and route6's """

	# TODO reimplement this using a trie

	cidr_types = ["inetnum", "inet6num", "route", "route6"]

	def __init__(self, database):
		self.database = database

	def get(self, type, primary_key):
		try:
			obj = self.database.get(type, primary_key)
		except KeyError:
			if type in self.cidr_types:
				search_list = [o for o in self.list() if o[0] == type]
				obj = self._find_by_cidr(search_list, primary_key)
				if obj:
					return self.get(obj[0][0], obj[0][1])
			raise

		return obj

	def find(self, primary_key):
		found_objs = set()
		objects = []

		for object in self.database.find(primary_key):
			objects.append(object)
			found_objs.add((object.type, object.primary_key))

		cidr_list = [kv for kv in self.list() if kv[0] in self.cidr_types]
		for object in self._find_by_cidr(cidr_list, primary_key):
			object = self.get(object[0], object[1])
			if (object.type, object.primary_key) in found_objs:
				continue
			objects.append(object)
			found_objs.add((object.type, object.primary_key))

		return objects

	def list(self):
		return self.database.list()

	def _find_by_cidr(self, search_list, primary_key):
		primary_key = netaddr.IPNetwork(primary_key)
		objects = []
		for typ, key in search_list:
			key = netaddr.IPNetwork(key)
			if primary_key not in key:
				continue
			objects.append((key.prefixlen, (typ, str(key))))
		objects = sorted(objects, key=lambda o: o[0], reverse=True)

		return [obj[1] for obj in objects]

