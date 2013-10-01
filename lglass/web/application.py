# coding: utf-8

import functools

import bottle
import jinja2

import lglass.web.registry
import lglass.database

DEFAULT_CONFIG = {
	"database": "whois+lglass.database.file+file:.",
	"static": {
		"robots.txt": None
	}
}

def obj_urlize(str):
	return str.replace("/", "_")

def obj_deurlize(str):
	return str.replace("_", "/")

class Application(bottle.Bottle):
	_registry = None

	def __init__(self, *args, **kwargs):
		__config = kwargs.pop("config", DEFAULT_CONFIG)
		kwargs.update({
			"autojson": False,
			"catchall": True
		})
		bottle.Bottle.__init__(self, *args, **kwargs)
		self.config = __config
		self._setup_routes()
		self._setup_jinja2()
	
	def _setup_routes(self):
		self.route("/", "GET", self.index_handler)
		self.route("/robots.txt", "GET", self.robots_txt_handler)
		self.route("/search", "POST", self.dummy_handler)
		self.route("/search/<query>", "GET", self.dummy_handler)
		self.route("/as", "GET", self.dummy_handler)
		self.route("/as/<asn>", "GET", self.dummy_handler)
		self.route("/obj", "GET", self._with_app(lglass.web.registry.show_object_types))
		self.route("/obj/<type>", "GET", self._with_app(lglass.web.registry.show_objects))
		self.route("/obj/<type>/<primary_key>", "GET", self._with_app(lglass.web.registry.show_object))

	def _setup_jinja2(self):
		self.jinja2 = jinja2.Environment(
			loader=jinja2.PackageLoader("lglass.web", "templates"))
		self.jinja2.filters["obj_urlize"] = obj_urlize
		self.jinja2.filters["obj_deurlize"] = obj_deurlize
	
	def _with_app(self, func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			return func(app=self, *args, **kwargs)
		return wrapper
	
	def render(self, _tpl, _dict={}, **kwargs):
		vars = kwargs.copy()
		vars.update(_dict)
		return self.jinja2.get_template(_tpl).render(vars)
	
	def index_handler(self):
		return self.render("index.html")

	def robots_txt_handler(self):
		try:
			return open(self.config["static"]["robots.txt"])
		except (TypeError, KeyError):
			self.abort(404, "File not found")
	
	@property
	def registry(self):
		if self._registry is None:
			self._registry = lglass.database.build_chain(self.config["database"])
		return self._registry

	dummy_handler = staticmethod(lambda: None)
	
	abort = staticmethod(bottle.abort)
	response = bottle.response
	request = bottle.request

app = application = Application()

