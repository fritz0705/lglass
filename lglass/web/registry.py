# coding: utf-8

import functools

import bottle

import lglass.database
import lglass.rpsl

from lglass.web.helpers import render_template, with_config

@with_config
def get_database(config):
	db = lglass.database.FileDatabase(config["registry"]["database"])
	return db

def with_db(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		return func(db=get_database(), *args, **kwargs)
	return wrapper

@with_db
def show_object_types(db):
	return render_template("registry/show_object_types.html", object_types=sorted(db.object_types))

@with_db
def show_objects(obj, db):
	objects = sorted((o for o in db.list() if o[0] == obj), key=lambda o: o[1])
	return render_template("registry/show_objects.html", objects=objects, object_type=obj)

@with_db
def show_object(obj, key, db):
	try:
		_obj = db.get(obj, key)
	except KeyError:
		bottle.abort(404, "Object not found")
	return render_template("registry/show_object.html", object=_obj)

@with_db
def show_raw_object(obj, key, db):
	bottle.response.content_type = "text/plain"
	try:
		return db.get(obj, key).pretty_print()
	except KeyError:
		bottle.abort(404, "Object not found")

@with_db
def find_objects(spec, db):
	return render_template("registry/find_obects.html", objects=db.find(spec))

