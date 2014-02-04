# coding: utf-8

import os.path

import lglass.rpsl

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

	def get_object(self, type, primary_key):
		raise NotImplementedError("get_object")

	def persist_object(self, object):
		raise NotImplementedError("persist_object")

	def delete_object(self, object):
		raise NotImplementedError("delete_object")

class FileSystemBackend(BaseBackend):
	def __init__(self, path):
		self.path = path

	def get_object(self, type, primary_key):
		with open(os.path.join(self.path, type, primary_key)) as fh:
			return lglass.rpsl.parse_rpsl(fh)
	
	def persist_object(self, object):
		with open(os.path.join(self.path, object.type, object.primary_key), "w") as fh:
			fh.write(object.pretty_print())
	
	def delete_object(self, type, primary_key):
		os.unlink(os.path.join(self.path, type, primary_key))

class DictBackend(object):
	def __init__(self, initial={}):
		self.data = dict(initial)
	
	def get_object(self, type, primary_key):
		return self.data[type, primary_key]

	def persist_object(self, object):
		self.data[object.type, object.primary_key] = object
	
	def delete_object(self, type, primary_key):
		del self.data[type, primary_key]
	
