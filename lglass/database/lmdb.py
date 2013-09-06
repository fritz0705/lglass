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
			raise TypeError("EXpected env_or_path to be lmdb.Environment or str, got {}".format(type(env_or_path)))

		with self.env.transaction() as txn:
			with txn.primary_database as db:
				if "+directory" not in db:
					db["+directory"] = json.dumps([])
	
	def get(self, type, primary_key):
		with self.env.transaction(lmdb.MDB_RDONLY) as txn:
			obj = txn["+".join((type, primary_key))].decode()
		return lglass.rpsl.Object.from_string(obj)

	def list(self):
		with self.env.transaction(lmdb.MDB_RDONLY) as txn:
			directory = txn["+directory"].decode()
		for entry in json.loads(directory):
			yield tuple(entry)

	def find(self, primary_key, types=None):
		with self.env.transaction(lmdb.MDB_RDONLY) as txn:
			directory = txn["+directory"].decode()
		for entry in json.loads(directory):
			if types is not None and entry[0] not in types:
				continue
			if entry[1] != primary_key:
				continue
			yield self.get(*entry)

	def save(self, object):
		with self.env.transaction() as txn:
			txn["+".join(object.spec)] = object.pretty_print()
			directory = json.loads(txn["+directory"].decode())
			if list(object.spec) not in directory:
				directory.append(list(object.spec))
				txn["+directory"] = json.dumps(directory)

	def delete(self, type, primary_key):
		with self.env.transaction() as txn:
			del txn["+".join((type, primary_key))]
			directory = json.loads(txn["+directory"].decode())
			directory.remove([type, primary_key])
			txn["+directory"] = json.dumps(directory)

	def __hash__(self):
		return hash(self.env)

	@classmethod
	def from_url(cls, url):
		return cls(url.path)

