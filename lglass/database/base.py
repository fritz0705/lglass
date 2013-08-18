# coding: utf-8

import urllib.parse

import lglass.rpsl

class Database(object):
	""" Database is an abstract class which defines some constants and setter/getter
	for subscripts. You have to extend from it by creating a new class and
	overriding __init__, get, list, find, save and delete to conform to the
	database protocol. """

	def __init__(self):
		raise NotImplementedError("Instances of Database are not permitted")

	def get(self, type, primary_key):
		""" Get specific object addressed by type and primary_key from database. Returns
		lglass.rpsl.Object. This method shall raise a KeyError if the object was not
		found. """
		raise NotImplementedError("get() is not implemented")

	def list(self, filter=None, limit=None):
		""" Return list of matching RPSL object specs, filter can be a callable taking
		two arguments (type, primary_key), and limit can be a int. RPSL object specs
		are tuples consisting of two str instances. """
		raise NotImplementedError("list() is not implemented")

	def find(self, key, types=None, limit=None):
		""" Finds an object by searching the whole database for key. It's possible
		to supply a list of acceptable object types and to provide a limit of objects.
		This method returns a list of lglass.rpsl.Object. """
		raise NotImplementedError("find() is not implemented")

	def save(self, obj):
		""" Save object in database. """
		raise NotImplementedError("save() is not implemented")

	def delete(self, type, primary_key):
		""" Delete object in database. """
		raise NotImplementedError("delete() is not implemented")

	object_types = {
		"as-block",
		"as-set",
		"aut-num",
		"dns",
		"filter-set",
		"inet6num",
		"inetnum",
		"inet-rtr",
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
		"route6",
		"route-set",
		"rtr-set"
	}

	def save_all(self, objs):
		for obj in objs:
			self.save(obj)

	def get_all(self):
		return (self.get(*spec) for spec in self.list())

	def schema(self, type):
		""" Return schema for type. Raises a KeyError if schema was not found.  """
		if type == "schema":
			return lglass.rpsl.SchemaObject.SCHEMA_SCHEMA
		name = type.upper() + "-SCHEMA"
		specs = [("schema", name), ("schemas", name), ("schema", type),
			("schemas", type)]
		obj = None
		for spec in specs:
			try:
				obj = self.get(*spec)
			except KeyError:
				continue
			break
		if obj is None:
			raise KeyError("schema({})".format(type))
		return lglass.rpsl.SchemaObject(obj)

	def __len__(self):
		return len(self.list())

	def __iter__(self):
		for type, primary_key in self.list():
			yield self.get(type, primary_key)

	def __contains__(self, key):
		if not isinstance(key, tuple):
			raise TypeError("Expected key to be tuple of length 2, got {}".format(key))
		try:
			self.get(*key)
		except KeyError:
			return False
		return True

	def __getitem__(self, key):
		if not isinstance(key, tuple):
			raise TypeError("Expected key to be tuple of length 2, got {}".format(key))
		return self.get(*key)
	
	def __delitem__(self, key):
		if not isinstance(key, tuple):
			raise TypeError("Expected key to be tuple of length 2, got {}".format(key))
		self.delete(*key)
	
url_schemes = {}

def register(name):
	def decorator(cls):
		if hasattr(cls, "from_url") and callable(cls.from_url):
			url_schemes[name] = cls
		return cls
	return decorator

def from_url(url):
	if isinstance(url, str):
		url = urllib.parse.urlparse(url)
	scheme = url.scheme
	if "+" in scheme:
		scheme = scheme.split("+")[-1]
	return url_schemes[scheme].from_url(url)

@register("dict")
class DictDatabase(Database):
	""" This database backend operates completely in memory by using a Python
	dictionary to organize the information. It uses only builtin Python data types
	like list, tuple, and dict. """

	def __init__(self):
		self.backend = dict()

	def save(self, object):
		self.backend[object.real_spec] = object
	
	def delete(self, type, primary_key):
		del self.backend[type, primary_key]
	
	def get(self, type, primary_key):
		return self.backend[type, primary_key]
	
	def list(self):
		return list(self.backend.keys())

	def find(self, primary_key, types=None):
		objects = []
		for type, pkey in self.backend.keys():
			if pkey != primary_key:
				continue
			if types is not None and type not in types:
				continue
			objects.append((type, pkey))
		return [self.get(*spec) for spec in objects]

	@classmethod
	def from_url(cls, url):
		return cls()

