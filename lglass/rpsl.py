# coding: utf-8

import os
import os.path

def parse_rpsl(lines):
	kv_pairs = []
	for line in lines:
		if not line.strip():
			continue
		if line[0] == '%':
			continue
		kv_pairs.append(tuple(map(lambda p: p.strip(), line.split(":", 1))))
	return kv_pairs

class RPSLObject(list):
	def __init__(self, data=None, type=None):
		list.__init__(self)

		self.extend(data)

		if type is not None:
			self.type = type
		else:
			if data and len(self) > 0:
				self.type = self[0][0]
			else:
				raise Exception("Too unspecific")
	
	def extend(self, data):
		if isinstance(data, dict):
			for key, value in data.items():
				self.get(key).append(value)
		elif isinstance(data, str):
			self.extend(parse_rpsl(data))
		elif isinstance(data, list):
			for key, value in data:
				self.get(key).append(value)
		elif data is None:
			pass
		else:
			list.extend(self, data)

	def __getitem__(self, key):
		if isinstance(key, str):
			obj = self.get(key)
			if obj == []:
				raise KeyError(key)
			return obj[0]
		return list.__getitem__(self, key)

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
			self.get_as_block.__func__,
			self.get_dns.__func__
		]

	def __getitem__(self, key):
		obj = self.get(key)
		if obj is None:
			raise KeyError(key)

		return obj

	def get(self, query):
		for method in self.search_list:
			obj = method(self, query)
			if obj:
				return obj

		return None

	def get_object(self, type, query):
		try:
			with open(self._path("{0}/{1}".format(type, query))) as file:
				obj = RPSLObject(type, file.read())
		except IOError:
			return None
		return obj

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

		if query[0:2] != "AS":
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

	def get_dns(self, query):
		try:
			with open(self._path("dns/{0}".format(query))) as file:
				obj = RPSLObject("dns", file.read())
		except IOError:
			return None
		return obj

	def ls(self):
		return self.persons() + self.as_blocks() + self.autnums() + self.dns() + self.inet6nums() + self.inetnums() + self.routes() + self.route6s()
	
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
		return os.listdir(self._path("route"))

	def route6s(self):
		return os.listdir(self._path("route6"))

	def _path(self, path):
		return os.path.join(self.prefix, path)

