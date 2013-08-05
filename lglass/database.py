# coding: utf-8

import os.path
import time

import netaddr

import lglass.rpsl

class Database(object):
	__init__ = None

	get = None
	list = None
	find = None
	save = None
	delete = None

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
			with open(self._path_for(type, primary_key)) as f:
				obj = lglass.rpsl.Object.from_string(f.read())
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
		path = self._path_for(object.type, object.primary_key)
		try:
			os.makedirs(os.path.dirname(path))
		except FileExistsError:
			pass
		with open(path, "w") as fh:
			fh.write(object.pretty_print())

	def delete(self, type, primary_key):
		try:
			os.unlink(self._path_for(type, primary_key))
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
		cache_key = (object.type, object.primary_key)
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

	def __init__(self, db, **kwargs):
		self.database = db
		self.__dict__.update(kwargs)

	def get(self, type, primary_key):
		return self.database.get(type, primary_key)

	def find(self, primary_key, types=None):
		objects = []
		found_objects = set([])

		objects.extend([o for o in self.find_by_cidr(primary_key, types)
			if o.spec not in found_objects])
		found_objects = set([obj.spec for obj in objects])

		objects.extend([o for o in self.find_by_range(primary_key, types)
			if o.spec not in found_objects])
		found_objects = set([obj.spec for obj in objects])

		objects.extend([o for o in self.database.find(primary_key, types=types)
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

		return [self.get(*m[1]) for m in sorted(matches, key=lambda o: o[0])]

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

		return [self.get(*m[1]) for m in sorted(matches, key=lambda o: o[0])]

	def save(self, object):
		self.database.save(object)

	def delete(self, type, primary_key):
		self.database.delete(type, primary_key)

	def list(self):
		return self.database.list()

	def __hash__(self):
		return hash(self.database)

class DictDatabase(Database):
	""" This database backend operates completely in memory by using a Python
	dictionary to organize the information. It uses only builtin Python data types
	like list, tuple, and dict. """

	def __init__(self):
		self.backend = dict()

	def save(self, object):
		self.backend[object.spec] = object
	
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

import sqlite3

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
			raise ValueError("Expected sql to be tuple, str or sqlite3.Connection, got {}".format(type(sql)))
		self.install_schema()

	def install_schema(self):
		c = self.connection.cursor()
		c.executescript(self.SQL_SCHEMA)
		c.close()
	
	def get(self, type, primary_key):
		with self.connection:
			cur = self.connection.cursor()
			cur.execute("SELECT id FROM 'objects' WHERE \"type\" = ? AND \"primary_key\" = ?", (type, primary_key))

			col = cur.fetchone()
			if col is None:
				return None

			obj = lglass.rpsl.Object()
			cur.execute("SELECT key, value FROM 'kvpairs' WHERE \"object_id\" = ? ORDER BY \"order\"", (col[0], ))
			
			obj.add(type, primary_key)

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
			cur.execute("SELECT id FROM 'objects' WHERE \"type\" = ? AND \"primary_key\" = ?", (object.type, object.primary_key))
			f = cur.fetchone()
			if f is not None:
				cur.execute("DELETE FROM 'objects' WHERE \"id\" = ?", (f[0], ))

			cur.execute("INSERT INTO 'objects' ('type', 'primary_key') VALUES (?, ?)", (object.type, object.primary_key))
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

