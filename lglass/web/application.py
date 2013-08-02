# coding: utf-8

import bottle

from lglass.web.helpers import render_template

app = bottle.Bottle()

def static_handler(path):
	return ""

def index_handler():
	return render_template("index.html")

app.route("/static/<path:path>", "GET", static_handler)

app.route("/", "GET", index_handler)

import lglass.web.registry

app.route("/registry", "GET", lglass.web.registry.show_object_types)
app.route("/registry/<obj>", "GET", lglass.web.registry.show_objects)
app.route("/registry/find/<spec>", "GET", lglass.web.registry.find_objects)
app.route("/registry/<obj>/<key>", "GET", lglass.web.registry.show_object)

