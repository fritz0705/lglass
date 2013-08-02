# coding: utf-8

import functools

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
	return render_template("registry/show_object_types.html", object_types=db.object_types)

@with_db
def show_objects(obj, db):
	objects = [o for o in db.list() if o[0] == obj]
	return render_template("registry/show_objects.html", objects=objects, object_type=obj)

@with_db
def show_object(obj, key, db):
	_obj = db.get(obj, key)
	return render_template("registry/show_object.html", object=_obj)

@with_db
def find_objects(spec, db):
	return render_template("registry/find_obects.html", objects=db.find(spec))

