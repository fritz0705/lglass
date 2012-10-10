# coding: utf-8

from lglass.web import application, jinja2_env
from lglass import bird_client, registry

@application.route("/as/<asn>")
def get_as(asn):
	asn = int(asn)
	obj = registry.get_autnum(asn)
	routes = bird_client.get_routes()
	routes = list(filter(lambda r: r.as_path[-1] == asn, routes))
	networks = set(map(lambda r: r.network, routes))

	return jinja2_env.get_template("lg/as.html").render(rpsl=obj, asn=asn, routes=routes, networks=networks)

