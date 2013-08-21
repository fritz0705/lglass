# coding: utf-8

import time

import lglass.database.base
import lglass.rpsl

@lglass.database.base.register("cached")
class CachedDatabase(lglass.database.base.Database):
	""" Simple in-memory cache for any database type. Will cache any object and
	flush it on request. """

	version_field = "x-cache-version"

	def __init__(self, database, **kwargs):
		self.database = database
		self.cache = {}

		self.__dict__.update(kwargs)

	def get(self, type, primary_key):
		cache_key = (type, primary_key)

		if cache_key in self.cache:
			return self.cache[cache_key]

		obj = self.database.get(type, primary_key)
		if self.version_field:
			obj.add(self.version_field, str(int(time.time())))

		self.cache[cache_key] = obj

		return obj
	
	def list(self):
		cache_key = "list"

		if cache_key in self.cache:
			return self.cache[cache_key]

		ls = self.database.list()
		self.cache[cache_key] = list(ls)

		return self.cache[cache_key]

	def find(self, primary_key, types=None):
		cache_key = (types, primary_key)

		if cache_key in self.cache:
			return self.cache[cache_key]

		objs = self.database.find(primary_key, types=types)
		if self.version_field:
			for obj in objs:
				obj.add(self.version_field, str(int(time.time())))
		self.cache[cache_key] = list(objs)

		return self.cache[cache_key]

	def save(self, object):
		self.database.save(object)
		cache_key = object.real_spec
		self.cache[cache_key] = object

	def delete(self, type, primary_key):
		self.database.delete(object)
		cache_key = (type, primary_key)
		del self.cache[cache_key]

	def flush(self):
		self.cache = {}

	def __hash__(self):
		return hash(self.database)

	@classmethod
	def from_url(cls, url):
		return cls(None)

