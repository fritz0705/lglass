# coding: utf-8

from lglass.web import application, jinja2_env, bird_client
import bottle
import lglass
import functools

@application.route("/")
def index():
	routes = filter(lambda route: type(route) == lglass.bird.BGPRoute, bird_client.get_routes())

	as_numbers = [ route.as_path for route in routes ]
	as_numbers = [ item for sublist in as_numbers for item in sublist ]
	as_numbers = list(set(as_numbers))
	as_numbers.sort()
	return jinja2_env.get_template("home/index.html").render(as_numbers=as_numbers)

@application.route("/search")
def search():
	obj = bottle.request.params["q"]

@application.route("/as/<asn>")
def show_as(asn):
	asn = int(asn)
	routes = filter(lambda route: type(route) == lglass.bird.BGPRoute, bird_client.get_routes())
	routes = filter(lambda route: asn in route.as_path, routes)

	origin_routes = filter(lambda route: asn == route.as_path[-1], routes)

