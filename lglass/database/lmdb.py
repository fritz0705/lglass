# coding: utf-8

import json

import lmdb

import lglass.rpsl
import lglass.database.base

@lglass.database.base.register("lmdb")
class LMDBDatabase(lglass.database.base.Database):
	def __init__(self, env_or_path, lib=None):
		if isinstance(env_or_path, lmdb.Environment):
			self.env = env_or_path
		elif isinstance(env_or_path, str):
			if lib is None:
				lib = lmdb.LibLMDB()
			elif isinstance(lib, str):
				lib = lmdb.LibLMDB(lib)
			elif isinstance(lib, lmdb.LibLMDB):
				pass
			else:
				raise TypeError("Expected lib to be None, str or lmdb.LibLMDB, got {}".format(type(lib)))

			self.env = lmdb.Environment(lib)
			self.env.open(env_or_path)
		else:
			raise TypeError("Expected env_or_path to be lmdb.Environment or str, got {}".format(type(env_or_path)))
	
	def get(self, type, primary_key):
		with self.env.transaction(lmdb.MDB_RDONLY) as txn:
			key = "\0".join((type, primary_key))
			obj = txn[key].decode()
		obj = lglass.rpsl.Object.from_string(obj)
		obj.real_type = type
		obj.real_primary_key = primary_key
		return obj

	def list(self):
		with self.env.transaction(lmdb.MDB_RDONLY) as txn:
			for key, value in txn.cursor():
				yield tuple(key.decode().split("\0"))

	def find(self, primary_key, types=None):
		with self.env.transaction(lmdb.MDB_RDONLY) as txn:
			for key, value in txn.cursor():
				type, pk = key.decode().split("\0")
				if types is not None and type in types:
					continue
				if primary_key != pk:
					continue
				obj = lglass.rpsl.Object.from_string(value.decode())
				obj.real_type = type
				obj.real_primary_key = pk
				yield obj

	def save(self, object):
		with self.env.transaction() as txn:
			key = "\0".join(object.real_spec)
			txn[key] = object.pretty_print()

	def delete(self, type, primary_key):
		with self.env.transaction() as txn:
			del txn["\0".join((type, primary_key))]

	def __hash__(self):
		return hash(self.env)

	@classmethod
	def from_url(cls, url):
		return cls(url.path)

