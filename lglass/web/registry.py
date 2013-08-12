# coding: utf-8

import functools

import bottle

import lglass.database
import lglass.rpsl

from lglass.web.helpers import render_template, with_config

@with_config
def get_database(config):
	db = lglass.database.FileDatabase(config["registry"]["database"])
	db = lglass.database.CIDRDatabase(db)
	return db

def with_db(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		return func(db=get_database(), *args, **kwargs)
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
			bottle.redirect("/obj/{type}/{key}".format(type=obj.type, key=obj.primary_key))
	else:
		bottle.abort(404, "Nothing found")

@with_db
def show_object(type, primary_key, db):
	try:
		obj = db.get(type, primary_key)
	except KeyError:
		bottle.abort(404, "Object not found")
	return render_template("registry/show_object.html", object=obj)

