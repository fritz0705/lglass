# coding: utf-8

import os.path
import netaddr

import lglass.rpsl

class NotFoundError(KeyError):
	@property
	def backend(self):
		return self.args[0]

	@backend.setter
	def backend(self, new):
		self.args[0] = new

	@property
	def type(self):
		return self.args[1]

	@type.setter
	def type(self, new):
		self.args[1] = new
	
	@property
	def primary_key(self):
		return self.args[2]

	@primary_key.setter
	def primary_key(self, new):
		self.args[2] = new

class BaseBackend(object):
	object_types = {
		"as-block",
		"as-set",
		"aut-num",
		"domain",
		"filter-set",
		"inet-rtr",
		"inet6num",
		"inetnum",
		"irt",
		"key-cert",
		"mntner",
		"organisation",
		"peering-set",
		"person",
		"poem",
		"poetic-form",
		"role",
		"route",
		"route-set",
		"route6",
		"rtr-set"
	}

	def get_schema(self, type):
		return lglass.rpsl.SchemaObject(self.get_object("schema", type.upper() + "-SCHEMA"))

	def get_object(self, type, primary_key):
		raise NotImplementedError("get_object")

	def persist_object(self, object):
		raise NotImplementedError("persist_object")

	def delete_object(self, object):
		raise NotImplementedError("delete_object")

	def list_objects(self, type):
		raise NotImplementedError("list_objects")

	def query(self, query):
		types = self.object_types if query.types is None else query.types
		for type_ in types:
			try:
				yield self.get_object(type_, query.term)
			except NotFoundError:
				pass
	
	def query_ipaddress(self, query):
		ipaddr = netaddr.IPNetwork(query.term)
		for supernet in ipaddr.supernet():
			new_query = query.copy()
			new_query.term = str(supernet)
			yield from self.query(new_query)
	
	def query_autnum(self, query):
		for primary_key in self.list_objects("as-block"):
			primary_key = primary_key.relace("_", "-")
			begin, end = map(int, map(str.strip, primary_key.split("-", 1)))
			if self.autnum >= begin and self.autnum <= end:
				yield self.get_object("as-block", primary_key)

class FileSystemBackend(BaseBackend):
	def __init__(self, path):
		self.path = path

	def get_object(self, type, primary_key):
		try:
			primary_key = primary_key.replace("/", "_")
			with open(self._path(type, primary_key)) as fh:
				obj = lglass.rpsl.Object(lglass.rpsl.parse_rpsl(fh))
				obj.real_spec = (type, primary_key)
				return obj
		except FileNotFoundError:
			raise NotFoundError(self, type, primary_key)
	
	def persist_object(self, object):
		with open(self._path(*object.real_spec), "w") as fh:
			fh.write(object.pretty_print())
	
	def delete_object(self, type, primary_key):
		try:
			os.unlink(self._path(type, primary_key))
		except FileNotFoundError:
			pass

	def list_objects(self, type):
		for primary_key in os.listdir(self._path(type, "")):
			if primary_key[0] == '.':
				continue
			yield primary_key

	def _path(self, type, primary_key):
		return os.path.join(self.path, type, primary_key.replace("/", "_"))

