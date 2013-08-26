# coding: utf-8

import urllib.parse

import pymongo
import pymongo.database
import pymongo.uri_parser

import lglass.database.base
import lglass.rpsl

@lglass.database.base.register("mongodb")
class MongoDBDatabase(lglass.database.base.Database):
	def __init__(self, mongo, database="lglass"):
		if isinstance(mongo, str):
			mongo = pymongo.MongoClient(mongo)
		elif isinstance(mongo, (pymongo.MongoClient, pymongo.database.Database)):
			pass
		else:
			raise TypeError("Expected mongo to be str, pymongo.MongoClient or pymongo.Database, got {}".format(type(mongo)))
		
		if isinstance(mongo, pymongo.database.Database):
			self.db = mongo
		else:
			self.db = mongo[database]
	
	def get(self, type, primary_key):
		col = self._get_col(type)
		mobj = col.find_one({"_id": primary_key})
		if mobj is None:
			raise KeyError(type, primary_key)
		obj = lglass.rpsl.Object(mobj["data"])
		return obj

	def list(self):
		for type in self.object_types:
			col = self._get_col(type)
			for obj in col.find():
				yield (type, obj["_id"])
	
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
		col = self._get_col(object.type)
		col.save({"_id": object.primary_key, "data": object.to_json_form()})

	def delete(self, type, primary_key):
		col = self._get_col(type)
		col.remove({"_id": primary_key})

	def _get_col(self, type):
		return self.db[type.replace("-", "_")]
	
	@classmethod
	def from_url(cls, url):
		rurl = list(url)
		rurl[0] = "mongodb"
		rurl = urllib.parse.urlunparse(rurl)

		return cls(rurl)

