# coding: utf-8

import functools

import bottle

import lglass.database
import lglass.web.helpers
obj_urlize = lglass.web.helpers.obj_urlize

class RegistryApp(lglass.web.helpers.BaseApp):
	DEFAULT_CONFIG = {
		"database": [
			"whois+lglass.database.file+file:.",
			"whois+lglass.database.cidr+cidr:",
			"whois+lglass.database.schema+schema:?types-include=person,aut-num"
		]
	}

	def __init__(self, config=None):
		lglass.web.helpers.BaseApp.__init__(self, config=config)
		self.route("/search", "POST", self.handle_whois_query)
		self.route("/search/<query>", "GET", self.handle_whois_query)
		self.route("/objects", "GET", self.handle_show_object_types)
		self.route("/objects/<type>", "GET", self.handle_show_objects)
		self.route("/objects/<type>/<primary_key>", "GET", self.handle_show_object)
		self.route("/flush", "POST", self.handle_flush_cache)

	_database = None

	@property
	def database(self):
		if self._database is None:
			self.database = self.config.get("database", self.DEFAULT_CONFIG["database"])
		return self._database

	@database.setter
	def database(self, new_value):
		if isinstance(new_value, list):
			self._database = lglass.database.build_chain(new_value)
		elif isinstance(new_value, str):
			self._database = lglass.database.from_url(new_value)
		else:
			self._database = new_value

	def handle_whois_query(self, query=None):
		if bottle.request.method == "POST":
			query = bottle.request.forms["query"]
		objects = self.database.find(query)
		if len(objects):
			if len(objects) > 1:
				return self.render_template("registry/whois_query.html", objects=objects)
			else:
				object = objects.pop()
				bottle.redirect("/registry/objects/{}/{}".format(object.real_type, obj_urlize(object.real_primary_key)))
		else:
			bottle.abort(404, "Nothing found")
	
	def handle_show_object(self, type, primary_key):
		try:
			object = self.database.get(type, primary_key)
		except KeyError:
			bottle.abort(404, "Object not found")

		try:
			schema = self.database.schema(object.type)
		except KeyError:
			pass

		items = []
		for key, value in object:
			if schema is not None:
				inverse = list(schema.find_inverse(self.database, key, value))
			else:
				inverse = []
			if inverse:
				inverse = inverse[0].type
			else:
				inverse = None
			items.append((key, value, inverse))

		return self.render_template("registry/show_object.html", items=items, object=object)

	def handle_show_objects(self, type):
		objects = [self.database.get(*spec) for spec in sorted(self.database.list())
				if spec[0] == type]
		return self.render_template("registry/show_objects.html", objects=objects, type=type)

	def handle_show_object_types(self):
		types = sorted(self.database.object_types)
		return self.render_template("registry/show_object_types.html", types=types)

	def handle_flush_cache(self):
		if getattr(self.database, "flush") and callable(self.database.flush):
			self.database.flush()

