# coding: utf-8

import os.path
import time
import socket
import json

import netaddr

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
	
class FileDatabase(Database):
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
		objects = []

		for type in os.listdir(self.root_dir):
			if type not in self.object_types:
				continue

			for primary_key in os.listdir(os.path.join(self.root_dir, type)):
				if primary_key[0] == '.': continue
				objects.append((type, primary_key.replace("_", "/")))
		
		return objects

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

class CachedDatabase(Database):
	""" Simple in-memory cache for any database type. Will cache any object and
	flush it on request. """

	version_field = "x-cache-version"

	def __init__(self, database, **kwargs):
		self.database = database
		self.cache = {}

		self.__dict__.update(kwargs)

	def get(self, type, primary_key):
		cache_key = (type, primary_key)

		if cache_key in self.cache:
			return self.cache[cache_key]

		obj = self.database.get(type, primary_key)
		if self.version_field:
			obj.add(self.version_field, str(int(time.time())))

		self.cache[cache_key] = obj

		return obj
	
	def list(self):
		cache_key = "list"

		if cache_key in self.cache:
			return self.cache[cache_key]

		ls = self.database.list()
		self.cache[cache_key] = ls

		return ls

	def find(self, primary_key, types=None):
		cache_key = (types, primary_key)

		if cache_key in self.cache:
			return self.cache[cache_key]

		objs = self.database.find(primary_key, types=types)
		if self.version_field:
			for obj in objs:
				obj.add(self.version_field, str(int(time.time())))
		self.cache[cache_key] = objs

		return objs

	def save(self, object):
		self.database.save(object)
		cache_key = object.real_spec
		self.cache[cache_key] = object

	def delete(self, type, primary_key):
		self.database.delete(object)
		cache_key = (type, primary_key)
		del self.cache[cache_key]

	def flush(self):
		self.cache = {}

	def __hash__(self):
		return hash(self.database)

class CIDRDatabase(Database):
	""" Extended database type which is a layer between the user and another
	database. It performs CIDR matching and AS range matching on find calls. """
	# TODO reimplement this using a trie

	range_types = {"as-block"}
	cidr_types = {"inetnum", "inet6num", "route", "route6"}

	perform_range = True
	perform_cidr = True

	def __init__(self, db, **kwargs):
		self.database = db
		self.__dict__.update(kwargs)

	def get(self, type, primary_key):
		return self.database.get(type, primary_key)

	def find(self, primary_key, types=None):
		objects = []
		found_objects = set([])

		objects.extend([o for o in self.database.find(primary_key, types=types)
			if o.spec not in found_objects])
		found_objects = set([obj.spec for obj in objects])

		if self.perform_cidr:
			objects.extend([o for o in self.find_by_cidr(primary_key, types)
				if o.spec not in found_objects])
			found_objects = set([obj.spec for obj in objects])

		if self.perform_range:
			objects.extend([o for o in self.find_by_range(primary_key, types)
				if o.spec not in found_objects])
			found_objects = set([obj.spec for obj in objects])

		return objects

	def find_by_cidr(self, primary_key, types=None):
		cidr_types = self.cidr_types
		if types:
			cidr_types = cidr_types & set(types)

		try:
			primary_key = netaddr.IPNetwork(primary_key)
		except (ValueError, netaddr.core.AddrFormatError):
			return []
		matches = []

		for obj in self.list():
			if obj[0] not in cidr_types:
				continue
			obj_addr = netaddr.IPNetwork(obj[1])
			if primary_key in obj_addr:
				matches.append((obj_addr.prefixlen, obj))

		matches = sorted(matches, key=lambda o: o[0], reverse=True)
		return [self.get(*m[1]) for m in matches]

	def find_by_range(self, primary_key, types=None):
		range_types = self.range_types
		if types:
			range_types = range_types & set(types)

		try:
			primary_key = int(primary_key.replace("AS", ""))
		except ValueError:
			return []

		matches = []

		for obj in self.list():
			if obj[0] not in range_types:
				continue
			obj_range = tuple([int(x.strip()) for x in obj[1].split("/", 2)])
			if len(obj_range) != 2:
				raise ValueError("Expected obj_range to be 2. Your database might be broken")
			if primary_key >= obj_range[0] and primary_key <= obj_range[1]:
				matches.append(((obj_range[1] - obj_range[0]), obj))

		matches = sorted(matches, key=lambda o: o[0], reverse=True)
		return [self.get(*m[1]) for m in matches]

	def save(self, object):
		self.database.save(object)

	def delete(self, type, primary_key):
		self.database.delete(type, primary_key)

	def list(self):
		return self.database.list()

	def __hash__(self):
		return hash(self.database)

class SchemaDatabase(Database):
	""" The inverse databases resolves inverse relationships on find() and also
	validates the schema of objects. """

	schema_validation_field = "x-schema-valid"
	hidden_attr_field = "x-hidden"

	hide_attributes = True
	resolve_inverse = True

	inverse_type_filter = staticmethod(lambda key: True)

	def __init__(self, db, **kwargs):
		self.database = db
		self.__dict__.update(kwargs)

	def get(self, type, primary_key):
		obj = self.database.get(type, primary_key)
		if self.schema_validation_field:
			self._validate_schema(obj)
		if self.hide_attributes:
			self._hide_attributes(obj)
		return obj

	def find(self, primary_key, types=None):
		objs = self.database.find(primary_key, types)

		if self.resolve_inverse:
			objs.extend(self.find_inverse_objects(objs))

		if self.schema_validation_field is not None:
			for obj in objs:
				self._validate_schema(obj)
		if self.hide_attributes:
			for obj in objs:
				self._hide_attributes(obj)

		return objs

	def save(self, object):
		self.database.save(object)

	def delete(self, type, primary_key):
		self.database.delete(type, primary_key)

	def list(self):
		return self.database.list()

	def __hash__(self):
		return hash(self.database)

	def find_inverse_objects(self, objs):
		if isinstance(objs, lglass.rpsl.Object):
			objs = [objs]
		seen = set(obj.spec for obj in objs)
		inverse_objs = []
		for obj in objs:
			try:
				schema = self.schema(obj.type)
			except KeyError:
				continue
			for constraint in schema.constraints():
				if constraint.inverse is None:
					continue

				for inverse in constraint.inverse:
					for key, value in obj.get(constraint.key_name):
						if not self.inverse_type_filter(inverse):
							continue
						if (inverse, value) not in seen:
							try:
								inv_obj = self.get(inverse, value)
							except KeyEror:
								pass
							else:
								seen.add((inverse, value))
								inverse_objs.append(inv_obj)
		return inverse_objs
	
	def _validate_schema(self, obj):
		if self.schema_validation_field in obj:
			return
		try:
			schema = self.schema(obj.type)
			schema.validate(obj)
		except lglass.rpsl.SchemaValidationError as e:
			obj.add(self.schema_validation_field, "INVALID {} {}".format(e.args[0], e.args[1]))
		except KeyError:
			obj.add(self.schema_validation_field, "UNKNOWN")
		else:
			obj.add(self.schema_validation_field, "VALID")
	
	def _hide_attributes(self, obj):
		try:
			schema = self.schema(obj.type)
		except KeyError:
			return

		hidden = set()

		for constraint in schema.constraints():
			if constraint.hidden:
				hidden.add(constraint.key_name)
				del obj[constraint.key_name]

		if self.hidden_attr_field and hidden:
			obj[self.hidden_attr_field] = " ".join(sorted(hidden))

InverseDatabase = SchemaDatabase

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

try:
	import sqlite3
except ImportError:
	sqlite3 = None

class SQLite3Database(Database):
	""" This database backend operates on a SQLite3 database and supports generic
	RPSL types. Additional, it provides fast access support for the standard RPSL
	types by allocating one table per standard type. Non-standard types are saved
	in the generic "objects" table. """

	SQL_SCHEMA = ("""
CREATE TABLE IF NOT EXISTS 'objects' (
	'id' INTEGER PRIMARY KEY,
	'type' STRING NOT NULL,
	'primary_key' STRING NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS 'objects_idx_type_primary_key' ON 'objects' (
	'type', 'primary_key'
);
CREATE TABLE IF NOT EXISTS 'kvpairs' (
	'id' INTEGER PRIMARY KEY,
	'object_id' INTEGER NOT NULL,
	'key' STRING NOT NULL,
	'value' STRING NOT NULL,
	'order' INTEGER NOT NULL,
	FOREIGN KEY ('object_id') REFERENCES 'objects' ('id') ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS 'kvpairs_idx_object_id' ON 'kvpairs' (
	'object_id'
);
PRAGMA foreign_keys = ON;
""")

	def __init__(self, sql):
		if isinstance(sql, sqlite3.Connection):
			self.connection = sql
		elif isinstance(sql, str):
			self.connection = sqlite3.connect(sql)
		elif isinstance(sql, tuple):
			self.connection = sqlite3.connect(*sql)
		else:
			raise TypeError("Expected sql to be tuple, str or sqlite3.Connection, got {}".format(type(sql)))
		self.install_schema()

	def install_schema(self):
		c = self.connection.cursor()
		c.executescript(self.SQL_SCHEMA)
		c.close()
	
	def get(self, type, primary_key):
		with self.connection:
			cur = self.connection.cursor()
			cur.execute("SELECT id, primary_key, type FROM 'objects' WHERE \"type\" = ? AND \"primary_key\" = ?", (type, primary_key))

			col = cur.fetchone()
			if col is None:
				raise KeyError(repr((type, primary_key)))

			obj = lglass.rpsl.Object()
			cur.execute("SELECT key, value FROM 'kvpairs' WHERE \"object_id\" = ? ORDER BY \"order\"", (col[0], ))
			
			obj.add(type, primary_key)
			if col[1] != primary_key:
				obj.real_primary_key = col[1]
			if col[2] != type:
				obj.real_type = col[2]

			for row in cur.fetchall():
				obj.add(row[0], row[1])

			cur.close()
			return obj

	def list(self):
		with self.connection:
			cur = self.connection.cursor()
			cur.execute("SELECT type, primary_key FROM 'objects'")

			objects = []
			for obj in cur.fetchall():
				objects.append((obj[0], obj[1]))
			cur.close()
			return objects

	def delete(self, type, primary_key):
		with self.connection:
			cur = self.connection.cursor()
			cur.execute("DELETE FROM 'objects' WHERE \"type\" = ? AND \"primary_key\" = ?", (type, primary_key))
			cur.close()

	def save(self, object):
		with self.connection:
			cur = self.connection.cursor()
			cur.execute("SELECT id FROM 'objects' WHERE \"type\" = ? AND \"primary_key\" = ?", (object.real_type, object.real_primary_key))
			f = cur.fetchone()
			if f is not None:
				cur.execute("DELETE FROM 'objects' WHERE \"id\" = ?", (f[0], ))

			cur.execute("INSERT INTO 'objects' ('type', 'primary_key') VALUES (?, ?)", (object.real_type, object.real_primary_key))
			new_id = cur.lastrowid

			for offset, (key, value) in enumerate(object[1:]):
				cur.execute("INSERT INTO 'kvpairs' ('object_id', 'key', 'value', 'order') VALUES (?, ?, ?, ?)",
					(new_id, key, value, offset))
			cur.close()
	
	def find(self, primary_key, types=None):
		specs = []

		with self.connection:
			cur = self.connection.cursor()
			if types is not None:
				for type in types:
					cur.execute("SELECT id FROM 'objects' WHERE \"type\" = ? AND \"primary_key\" = ?", (type, primary_key))
					f = cur.fetchone()
					if f is not None:
						specs.append((type, primary_key))
			else:
				cur.execute("SELECT type, id FROM 'objects' WHERE \"primary_key\" = ?", (primary_key, ))
				for col in cur.fetchall():
					specs.append((col[0], primary_key))
			cur.close()

		return [self.get(*spec) for spec in specs]

class WhoisClientDatabase(Database):
	def __init__(self, hostspec):
		self.hostspec = hostspec
	
	def get(self, type, primary_key):
		try:
			return self.find(primary_key, types=[type])[-1]
		except IndexError:
			raise KeyError(type, primary_key)

	def find(self, primary_key, types=None):
		send_buffer = b""
		recv_buffer = b""

		if types is not None:
			send_buffer += "-T {types} ".format(types=",".join(types)).encode()
		send_buffer += "{key}".format(key=primary_key).encode()
		send_buffer += b"\r\n"

		with socket.create_connection(self.hostspec) as sock:
			while len(send_buffer):
				sent = sock.send(send_buffer)
				send_buffer = send_buffer[sent:]
			while True:
				recvd = sock.recv(1024)
				if not len(recvd):
					break
				recv_buffer += recvd

		lines = recv_buffer.decode().splitlines()
		lines_iter = iter(lines)

		objs = []

		while True:
			obj = lglass.rpsl.Object.from_iterable(lines_iter, pragmas={
				"stop-at-empty-line": True
			})
			if not obj:
				break
			objs.append(obj)

		return objs

	def list(self):
		raise NotImplementedError("list() is not supported for WhoisClientDatabase")

	def save(self):
		raise NotImplementedError("save() is not supported for WhoisClientDatabase")

	def delete(self):
		raise NotImplementedError("delete() is not supported for WhoisClientDatabase")

try:
	import redis
except ImportError:
	redis = None

class RedisDatabase(Database):
	def __init__(self, db, _redis, timeout=600, prefix="lglass:"):
		if isinstance(_redis, redis.Redis):
			self.redis = _redis
		elif isinstance(_redis, dict):
			self.redis = redis.Redis(**_redis)
		elif isinstance(_redis, tuple):
			self.redis = redis.Redis(*_redis)
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
			listing = self.database.list()
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
			results = self.database.find(key, types)
			self.redis.set(self._key_for_find(key, types),
					self._serialize_find(results),
					ex=self.timeout)
		else:
			results = self._deserialize_find(results.decode())
		return results

	def save(self, obj):
		self.database.save(obj)
		self.redis.set(self._key_for(type, primary_key),
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

	def _key_for_find(self, key, types):
		return "{prefix}find+{key}+{types}".format(prefix=self.prefix,
			key=key, types=",".join(types))
	
	def _key_for_list(self):
		return "{prefix}list".format(prefix=self.prefix)

	def _key_for(self, type, primary_key):
		return "{prefix}{type}+{primary_key}".format(prefix=self.prefix,
			type=type, primary_key=primary_key)

def database_factory(config={}):
	""" Complex function to build a stack of databases for simple usage. It supports
	two database types: sqlite3 and file. You can specify the database type in
	config["type"]. It also supports caching in redis and in memory by providing
	config["caching.type"] """
	_config = {
		"type": config.get("type", "file"),
		"caching": config.get("caching", False),
		"caching.type": config.get("caching.type", "memory"),
		"caching.timeout": config.get("caching.timeout", 600),
		"cidr": config.get("cidr", False),
		"cidr.range_types": config.get("cidr.range_types", None),
		"cidr.cidr_types": config.get("cidr.cidr_types", None),
		"cidr.range": config.get("cidr.range", True),
		"cidr.cidr": config.get("cidr.cidr", True),
		"schema": config.get("schema", True),
		"schema.inverse.types": config.get("schema.inverse.types", { "aut-num", "person" }),
		"schema.inverse": config.get("schema.inverse", True),
		"schema.hide": config.get("schema.hide", True),
		"schema.validate": config.get("schema.validate", False)
	}
	if _config["type"] == "file":
		_config["path"] = config.get("path", ".")
		db = FileDatabase(_config["path"])
	elif _config["type"] == "sqlite3":
		_config["path"] = config.get("path", ":memory:")
		db = SQLite3Database(_config["path"])
	else:
		db = DictDatabase()
	
	if _config["caching"]:
		if _config["caching.type"] == "memory":
			db = CachedDatabase(db)
		elif _config["caching.type"] == "redis":
			_config["caching.url"] = config.get("caching.url", "redis://localhost:6379/0")
			db = RedisDatabase(db,
				redis.StrictRedis.from_url(_config["caching.url"]),
				timeout=_config["caching.timeout"])
	
	if _config["cidr"]:
		db = CIDRDatabase(db)
		if _config["cidr.range_types"] is not None:
			db.range_types = set(_config["cidr.range_types"])
		if _config["cidr.cidr_types"] is not None:
			db.range_types = set(_config["cidr.cidr_types"])
		if _config["range"] is False:
			db.perform_range = False
		if _config["cidr"] is False:
			db.perform_cidr = False
	
	if _config["schema"]:
		db = SchemaDatabase(db)
		db.resolve_inverse = _config["schema.inverse"]
		if _config["schema.inverse.types"] is not None:
			db.inverse_type_filter = lambda key: key in _config["schema.inverse.types"]
		db.hide_attributes = _config["schema.hide"]
		if _config["schema.validate"] is False:
			db.schema_validation_field = None
	
	return db
	
