# coding: utf-8

import bottle

import lglass.web.helpers
import lglass.web.registry

class MainApp(lglass.web.helpers.BaseApp):
	DEFAULT_CONFIG = {
	}

	def __init__(self, config=None):
		lglass.web.helpers.BaseApp.__init__(self)
		self.config = config

		self.registry_app = lglass.web.registry.RegistryApp(self.config.get("registry"))
		self.mount("/registry/", self.registry_app)

		self.route("/", "GET", self.handle_index)
	
	def handle_index(self):
		return self.render_template("index.html")

