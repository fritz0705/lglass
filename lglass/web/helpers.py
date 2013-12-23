# coding: utf-8

import functools
import os
import json

import jinja2
import bottle

class BaseApp(bottle.Bottle):
	__jinja2_env = None
	_config = None
	catchall = False
	DEFAULT_CONFIG = {}

	def __init__(self, config=None):
		self.routes = []
		self.router = bottle.Router()
		self.resources = bottle.ResourceManager()
		self.error_handler = {}
		self.plugins = []

		self.config = config

	@property
	def _jinja2_env(self):
		if self.__jinja2_env is None:
			self.__jinja2_env = jinja2.Environment(
				loader=jinja2.PackageLoader("lglass.web", "templates"))
			self.__jinja2_env.filters["obj_urlize"] = obj_urlize
			self.__jinja2_env.filters["obj_deurlize"] = obj_deurlize
		return self.__jinja2_env

	@_jinja2_env.setter
	def _jinja2_env(self, new_value):
		self.__jinja2_env = new_value

	@property
	def config(self):
		if self._config is None:
			self.config = self.DEFAULT_CONFIG
		return self._config
	
	@config.setter
	def config(self, new_value):
		if isinstance(new_value, str):
			self._config = json.loads(new_value)
		elif hasattr(new_value, "read"):
			self._config = json.load(new_value)
		else:
			self._config = new_value

	def render_template(self, tpl, **kwargs):
		return self._jinja2_env.get_template(tpl).render(kwargs)

	@property
	def request(self):
		return bottle.request

def obj_urlize(str):
	return str.replace("/", "_")

def obj_deurlize(str):
	return str.replace("_", "/")

