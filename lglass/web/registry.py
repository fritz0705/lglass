# coding: utf-8

from lglass.web import application, jinja2_env
from lglass import registry, bird_client
import bottle

@application.route("/reg/autnum/<query>")
def autnum(query):
	bottle.response.content_type = "text/plain"
	return str(registry.get_autnum(query))

@application.route("/reg/inetnum/<query>")
def inetnum(query):
	bottle.response.content_type = "text/plain"
	return str(registry.get_inetnum(query))

@application.route("/reg/route/<query>")
def route(query):
	bottle.response.content_type = "text/plain"
	return str(registry.get_route(query))

@application.route("/reg/any/<query>")
def any(query):
	bottle.response.content_type = "text/plain"
	objects = registry.get_all(query)
	objects = map(lambda o: str(o), objects)

	return "\n\n".join(objects)

