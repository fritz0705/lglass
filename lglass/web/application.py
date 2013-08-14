# coding: utf-8

import bottle

from lglass.web.helpers import render_template, with_config

app = bottle.Bottle()

def index_handler():
	return render_template("index.html")

@with_config
def robots_txt_handler(config):
	if config["robots.txt"] is not None:
		return open(config["robots.txt"])
	bottle.abort(404, "File not found")

app.route("/", "GET", index_handler)
app.route("/robots.txt", "GET", robots_txt_handler)

import lglass.web.registry

app.route("/obj", "GET", lglass.web.registry.show_object_types)
app.route("/obj/<type>", "GET", lglass.web.registry.show_objects)
app.route("/obj/<type>/<primary_key>", "GET", lglass.web.registry.show_object)

app.route("/whois/<query>", "GET", lglass.web.registry.whois_query)
app.route("/whois", "POST", lglass.web.registry.whois_query)

app.route("/flush", "POST", lglass.web.registry.flush_cache)

