# coding: utf-8

import os
import os.path

import lglass.rpsl

class FileRegistry(object):
	object_types = {"as-block", "as-set", "aut-num", "domain", "inet6num",
			"inetnum", "mntner", "organisation", "person", "route", "route6",
			"route-set", "schema"}

	def __init__(self, root_dir='.'):
		self.root_dir = root_dir

	def list(self):
		for type in os.listdir(self.root_dir):
			if type not in self.object_types:
				continue
			for primary_key in os.listdir(os.path.join(self.root_dir, type)):
				if primary_key[0] == '.': continue
				yield (type, primary_key.replace("_", "/"))

	def get(self, type, primary_key):
		obj = None
		try:
			with open(self.__path_for(type, primary_key)) as fh:
				obj = lglass.rpsl.Object.from_string(fh.read())
				if primary_key != obj.primary_key:
					obj.real_primary_key = primary_key
				if type != obj.type:
					obj.real_type = type
		except FileNotFoundError:
			raise KeyError(repr((type, primary_key)))
		except ValueError as verr:
			raise ValueError((type, primary_key), *verr.args)
		return obj

	def save(self, obj):
		with open(self.__path_for(*obj.real_spec), "w") as fh:
			fh.write(obj.pretty_print())

	def delete(self, type, primary_key):
		try:
			os.unlink(self.__path_for(type, primary_key))
		except FileNotFoundError:
			raise KeyError(repr((type, primary_key)))
	
	def lookup(self, specs):
		obj = None
		for spec in specs:
			try:
				obj = self.get(*spec)
			except KeyError:
				continue
			break
		if obj is None:
			raise KeyError(specs)
		return obj

	def schema(self, type):
		if type == "schema":
			return lglass.rpsl.SchemaObject.SCHEMA_SCHEMA

		name = type.upper() + "-SCHEMA"
		specs = [("schema", name), ("schemas", name), ("schema", type),
				("schemas", type)]
		try:
			return lglass.rpsl.SchemaObject(self.lookup(specs))
		except KeyError:
			raise KeyError("schema({})".format(type))

	def __path_for(self, type, primary_key):
		return os.path.join(self.root_dir, type, primary_key.replace("/", "_"))

	def __iter__(self):
		for type, primary_key in self.list():
			yield self.get(type, primary_key)
	
	def __len__(self):
		return len(list(self.list()))
	
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

