# coding: utf-8

import os
import os.path

class RPSLObject(list):
	def __init__(self, type, data):
		list.__init__(self)

		self.type = type
		self.extend(data)
	
	def extend(self, data):
		if isinstance(data, dict):
			for key, value in data.items():
				self.get(key).append(value)
		elif isinstance(data, str):
			kv_pairs = []
			for line in data.split("\n"):
				if not line.strip():
					continue
				kv_pairs.append(tuple(map(lambda p: p.strip(), line.split(":", 1))))
			self.extend(kv_pairs)
		elif isinstance(data, list):
			for key, value in data:
				self.get(key).append(value)
		else:
			list.extend(self, data)

	def get(self, key):
		for _key, value in self:
			if _key == key:
				return value

		l = []
		self.append((key, l))
		return l
	
	def __str__(self):
		string = []
		for key, values in self:
			for value in values:
				string.append("{0}: {1}".format(key, value))
		return "\n".join(string)

class Database:
	def __init__(self, prefix="dn42"):
		self.prefix = prefix
		self.search_list = [
			self.get_autnum.__func__,
			self.get_person.__func__,
			self.get_inetnum.__func__,
			self.get_inet6num.__func__,
			self.get_route.__func__,
			self.get_route6.__func__,
			self.get_as_block.__func__
		]

	def get(self, query):
		for method in self.search_list:
			obj = method(self, query)
			if obj:
				return obj

		return None

	def get_all(self, query):
		result = []
		for method in self.search_list:
			obj = method(self, query)
			if obj:
				result.append(obj)

		return result

	def get_autnum(self, query):
		if type(query) != str:
			query = str(query)

		if query[0:1] != "AS":
			query = "AS" + query

		try:
			with open(self._path("aut-num/{0}".format(query))) as file:
				obj = RPSLObject("aut-num", file.read())
		except IOError:
			return None

		return obj
	
	def get_person(self, name):
		try:
			with open(self._path("person/{0}".format(name))) as file:
				obj = RPSLObject("person", file.read())
		except IOError:
			return None
		return obj

	def get_inetnum(self, query):
		query = str(query)
		query = query.replace("/", "_")

		try:
			with open(self._path("inetnum/{0}".format(query))) as file:
				obj = RPSLObject("inetnum", file.read())
		except IOError:
			return None
		return obj

	def get_inet6num(self, query):
		query = str(query)
		query = query.replace("/", "_")
		try:
			with open(self._path("inet6num/{0}".format(query))) as file:
				obj = RPSLObject("inet6num", file.read())
		except IOError:
			return None
		return obj

	def get_route(self, query):
		query = str(query)
		query = query.replace("/", "_")

		try:
			with open(self._path("route/{0}".format(query))) as file:
				obj = RPSLObject("route", file.read())
		except IOError:
			return None
		return obj

	def get_route6(self, query):
		query = str(query)
		query = query.replace("/", "_")

		try:
			with open(self._path("route6/{0}".format(query))) as file:
				obj = RPSLObject("route6", file.read())
		except IOError:
			return None
		return obj

	def get_as_block(self, query):
		if isinstance(query, range) or isinstance(query, list):
			query = "{0}_{1}".format(query[0], query[-1])

		try:
			with open(self._path("as-block/{0}".format(query))) as file:
				obj = RPSLObject("as-block", file.read())
		except IOError:
			return None
		return obj
	
	def persons(self):
		return os.listdir(self._path("person"))

	def as_blocks(self):
		return os.listdir(self._path("as-block"))

	def autnums(self):
		return os.listdir(self._path("aut-num"))

	def dns(self):
		return os.listdir(self._path("dns"))

	def inet6nums(self):
		return os.listdir(self._path("inet6num"))

	def inetnums(self):
		return os.listdir(self._path("inetnum"))

	def routes(self):
		return os.listdir(self._path("routes"))

	def route6s(self):
		return os.listdir(self._path("route6s"))

	def _path(self, path):
		return os.path.join(self.prefix, path)

