# coding: utf-8

from lglass.web import application, jinja2_env
from lglass import registry, bird_client
import netaddr
import pprint
import bottle

@application.route("/search")
def search():
	query = bottle.request.params.get("q", "")
	objects = registry.get_all(query)

	try:
		network = netaddr.IPNetwork(query)

		routes = bird_client.get_routes()
		routes = list(filter(lambda r: network in r.network, routes))
	except netaddr.core.AddrFormatError:
		routes = []
	
	return jinja2_env.get_template("search.html").render(objects=objects, routes=routes, query=query)
