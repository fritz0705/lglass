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
		if line[0] == ' ':
			new_entry = kv_pairs[-1][1] + " " + line.strip()
			kv_pairs[-1] = (kv_pairs[-1][0], new_entry)
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
			self.extend(parse_rpsl(data.split("\n")))
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
	
	def name(self):
		return self[self.type]

	def handle(self):
		return self["nic-hdl"]
	
	def __str__(self):
		string = []
		for key, values in self:
			for value in values:
				string.append("{0}: {1}".format(key, value))
		return "\n".join(string)

class MemoryDatabase:
	def __init__(self):
		self.persons = {}
		self.autnums = {}

	def update(self, other):
		for person in other.persons():
			person = other.get_person(person)
			self.persons[person.handle()] = person

		for autnum in other.autnums():
			print(autnum)
			autnum = other.get_autnum(autnum)
			number = int(autnum.name().replace("AS", ""))
			self.autnums[number] = autnum
	
	def get_autnum(self, autnum):
		if isinstance(query, str):
			query = int(query.replace("AS", ""))

		try:
			return self.autnums[query]
		except:
			return None
	
	def get_person(self, person):
		try:
			return self.person[query]
		except:
			return None

	def persons(self):
		return list(self.persons.keys())

	def autnums(self):
		return list(map(lambda k: "AS{0}".format(k), self.persons.keys()))

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
				obj = RPSLObject(file.read(), type=type)
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

		return self.get_object("aut-num", query)
	
	def get_person(self, name):
		return self.get_object("person", name)

	def get_inetnum(self, query):
		query = str(query)
		query = query.replace("/", "_")

		return self.get_object("inetnum", query)

	def get_inet6num(self, query):
		query = str(query)
		query = query.replace("/", "_")

		return self.get_object("inet6num", query)

	def get_route(self, query):
		query = str(query)
		query = query.replace("/", "_")

		return self.get_object("route", query)

	def get_route6(self, query):
		query = str(query)
		query = query.replace("/", "_")

		return self.get_object("route6", query)

	def get_as_block(self, query):
		if isinstance(query, range) or isinstance(query, list):
			query = "{0}_{1}".format(query[0], query[-1])

		return self.get_object("as-block", query)

	def get_dns(self, query):
		return self.get_object("dns", query)

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

	def update(self, other):
		raise NotImplemented()

