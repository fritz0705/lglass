# coding: utf-8

import redis
import json
import hashlib
import urllib.parse

import lglass.database.base
import lglass.rpsl

@lglass.database.base.register("redis")
class RedisDatabase(lglass.database.base.Database):
	""" Caching database layer which uses redis to cache the objects and search
	results, but without redundant caching like CachedDatabase """

	hash_algorithm = "sha1"
	key_format = None

	def __init__(self, db, _redis, timeout=600, prefix="lglass:"):
		if isinstance(_redis, redis.Redis):
			self.redis = _redis
		elif isinstance(_redis, dict):
			self.redis = redis.Redis(**_redis)
		elif isinstance(_redis, tuple):
			self.redis = redis.Redis(*_redis)
		elif isinstance(_redis, str):
			self.redis = redis.Redis.from_url(_redis)
		else:
			raise TypeError("Expected redis.Redis, dict or tuple as redis instance, got {}".format(type(_redis)))

		self.database = db
		self.timeout = timeout
		self.prefix = prefix

	def get(self, type, primary_key):
		obj = self.redis.get(self._key_for(type, primary_key))
		if obj is None:
			obj = self.database.get(type, primary_key)
			self.redis.set(self._key_for(type, primary_key),
				self._serialize(obj),
				ex=self.timeout)
		else:
			obj = self._deserialize(obj.decode())
		return obj
	
	def list(self):
		listing = self.redis.get(self._key_for_list())
		if listing is None:
			listing = list(self.database.list())
			self.redis.set(self._key_for_list(),
				self._serialize_listing(listing),
				ex=self.timeout)
		else:
			listing = self._deserialize_listing(listing.decode())
		return listing

	def find(self, key, types=None):
		if types is None:
			types = self.object_types
		results = self.redis.get(self._key_for_find(key, types))
		if results is None:
			results = list(self.database.find(key, types))
			self.redis.set(self._key_for_find(key, types),
					self._serialize_find(results),
					ex=self.timeout)
		else:
			results = self._deserialize_find(results.decode())
		return results

	def save(self, obj):
		self.database.save(obj)
		self.redis.set(self._key_for(obj.type, obj.primary_key),
			self._serialize(obj),
			ex=self.timeout)

	def delete(self, type, primary_key):
		self.database.delete(type, primary_key)
		self.redis.delete(self._key_for(type, primary_key))

	def _serialize(self, obj):
		return json.dumps(obj.to_json_form())

	def _deserialize(self, string):
		return lglass.rpsl.Object(json.loads(string))

	def _serialize_listing(self, listing):
		result = [[key, value] for key, value in listing]
		return json.dumps(result)
	
	def _deserialize_listing(self, string):
		listing = json.loads(string)
		return [(key, value) for key, value in listing]

	def _serialize_find(self, finds):
		result = [list(obj.real_spec) for obj in finds]
		return json.dumps(result)

	def _deserialize_find(self, string):
		finds = json.loads(string)
		result = []
		for spec in finds:
			result.append(self.get(*spec))
		return result

	def _key_hash(self, key):
		h = hashlib.new(self.hash_algorithm)
		h.update(key.encode())
		if self.key_format:
			return self.key_format.format(h.hexdigest())
		else:
			return self.prefix + h.hexdigest()

	def _key_for_find(self, key, types):
		return self._key_hash("find+{key}+{types}".format(
			key=key, types=",".join(types)))
	
	def _key_for_list(self):
		return self._key_hash("list")

	def _key_for(self, type, primary_key):
		return self._key_hash("{type}+{primary_key}".format(prefix=self.prefix,
			type=type, primary_key=primary_key))
	
	@classmethod
	def from_url(cls, url):
		""" Create instance from URL which has the form
			
			whois+redis://{host}:{port}/{database}?timeout={n}&format={format}
		"""
		rurl = list(url)
		rurl[0] = "redis"
		rurl = urllib.parse.urlunparse(rurl)
		self = cls(None, redis.Redis.from_url(rurl))

		if url.query:
			query = urllib.parse.parse_qs(url.query)
			if "timeout" in query:
				self.timeout = int(query["timeout"][-1])
			if "format" in query:
				self.key_format = query["format"][-1]

		return self

