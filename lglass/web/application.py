# coding: utf-8

import bottle

from lglass.web.helpers import render_template

app = bottle.Bottle()

def static_handler(path):
	return ""

def index_handler():
	return render_template("index.html")


app.route("/", "GET", index_handler)

import lglass.web.registry

app.route("/obj/<type>/<primary_key>", "GET", lglass.web.registry.show_object)
app.route("/whois/<query>", "GET", lglass.web.registry.whois_query)
app.route("/whois", "POST", lglass.web.registry.whois_query)

