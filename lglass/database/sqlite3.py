# coding: utf-8

try:
	import sqlite3
except ImportError:
	sqlite3 = None

import lglass.database.base
import lglass.rpsl

@lglass.database.base.register("sqlite3")
class SQLite3Database(lglass.database.base.Database):
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

			for obj in cur.fetchall():
				yield (obj[0], obj[1])
			cur.close()

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
	
	@classmethod
	def from_url(cls, url):
		return cls(url.path)

