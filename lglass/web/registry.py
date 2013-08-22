# coding: utf-8

import functools

import bottle

import lglass.database.file
import lglass.database.redis
import lglass.database.cache
import lglass.database.schema
import lglass.database.cidr
import lglass.rpsl

from lglass.web.helpers import render_template, with_config

@with_config
def get_database(config):
	if isinstance(config["registry"], list):
		db = lglass.database.base.build_chain(config["registry"])
		if "registry.types" in config:
			db.object_types = set(config["registry.types"])
		return db
	db = lglass.database.file.FileDatabase(config["registry.database"])
	if config["registry.cidr"]:
		db = lglass.database.cidr.CIDRDatabase(db)
	if config["registry.inverse"]:
		db = lglass.database.schema.InverseDatabase(db)
		if config["registry.inverse.types"]:
			db.inverse_type_filter = lambda key: key in config["registry.inverse.types"]
	if config["registry.caching"]:
		if config["registry.caching.type"] == "redis":
			db = lglass.database.redis.RedisDatabase(db,
				config["registry.caching.url"],
				timeout=config["registry.caching.timeout"],
				prefix=config["registry.caching.prefix"])
		else:
			db = lglass.database.cache.CachedDatabase(db)
	if "registry.types" in config:
		db.object_types = set(config["registry.types"])
	return db

def with_db(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		db = bottle.request.app.config.get("lglass.database")
		if db is None:
			db = get_database()
			bottle.request.app.config["lglass.database"] = db
		return func(db=db, *args, **kwargs)
	return wrapper

@with_db
def whois_query(db, query=None):
	if bottle.request.method == "POST":
		query = bottle.request.forms["query"]

	objs = db.find(query)
	if len(objs):
		if len(objs) > 1:
			return render_template("registry/whois_query.html", objects=objs)
		else:
			obj = objs.pop()
			bottle.redirect("/obj/{type}/{key}".format(type=obj.real_type,
				key=lglass.web.helpers.obj_urlize(obj.real_primary_key)))
	else:
		bottle.abort(404, "Nothing found")

@with_db
def show_object(type, primary_key, db):
	try:
		obj = db.get(type, primary_key)
	except KeyError:
		bottle.abort(404, "Object not found")

	try:
		schema = db.schema(obj.type)
	except KeyError:
		pass

	# (key, value, reference) => ("origin", "AS64712", "aut-num")
	items = []
	for key, value in obj:
		inverse = list(schema.find_inverse(db, key, value))
		if inverse:
			inverse = inverse[0]
		else:
			inverse = None
		items.append((key, value, inverse))

	return render_template("registry/show_object.html", items=items, object=obj)

@with_db
def show_objects(type, db):
	objs = [db.get(*spec) for spec in sorted(db.list()) if spec[0] == type]
	return render_template("registry/show_objects.html", objects=objs, type=type)

@with_db
def show_object_types(db):
	types = sorted(db.object_types)
	return render_template("registry/show_object_types.html", types=types)

@with_db
def flush_cache(db):
	if getattr(db, "flush") and callable(db.flush):
		db.flush()

