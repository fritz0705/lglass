# coding: utf-8

import os
import os.path

import lglass.rpsl
import lglass.database.base

@lglass.database.base.register("file")
class FileDatabase(lglass.database.base.Database):
	""" Simple database type which acts on a structured directory structure,
	where types are represented as directories and objects resp. their primary
	keys as files. """
	root_dir = '.'

	def __init__(self, root_dir='.'):
		self.root_dir = root_dir

	def __path_for(self, type, primary_key):
		return os.path.join(self.root_dir, type, primary_key.replace("/", "_"))

	def get(self, type, primary_key):
		obj = None
		try:
			with open(self.__path_for(type, primary_key)) as f:
				obj = lglass.rpsl.Object.from_string(f.read())
				if primary_key != obj.primary_key:
					obj.real_primary_key = primary_key
				if type != obj.type:
					obj.real_type = type
		except FileNotFoundError:
			raise KeyError(repr((type, primary_key)))
		return obj

	def list(self):
		for type in os.listdir(self.root_dir):
			if type not in self.object_types:
				continue

			for primary_key in os.listdir(os.path.join(self.root_dir, type)):
				if primary_key[0] == '.': continue
				yield (type, primary_key.replace("_", "/"))

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

	def save(self, object):
		path = self.__path_for(*object.real_spec)
		try:
			os.makedirs(os.path.dirname(path))
		except FileExistsError:
			pass
		with open(path, "w") as fh:
			fh.write(object.pretty_print())

	def delete(self, type, primary_key):
		try:
			os.unlink(self.__path_for(type, primary_key))
		except FileNotFoundError:
			raise KeyError(repr((type, primary_key)))

	def __hash__(self):
		return hash(self.root_dir) ^ hash(type(self))

	@classmethod
	def from_url(cls, url):
		return cls(url.path)

