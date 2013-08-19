# coding: utf-8

import functools
import os
import json

import jinja2
import bottle

env = jinja2.Environment(loader=jinja2.PackageLoader("lglass.web", "templates"))

def obj_urlize(str):
	return str.replace("/", "_")

def obj_deurlize(str):
	return str.replace("_", "/")

env.filters["obj_urlize"] = obj_urlize
env.filters["obj_deurlize"] = obj_deurlize

def render_template(tpl, **kwargs):
	return env.get_template(tpl).render(kwargs)

DEFAULT_CONFIG = {
	"registry": ["file:.", "cidr:", "schema:", "cached:"],
	"registry.database": ".",
	"registry.caching": True,
	"registry.cidr": True,
	"registry.inverse": True,
	"registry.inverse.types": None,
	"registry.caching.type": "caching",
	"registry.caching.url": "redis://localhost:6379/0",
	"registry.caching.prefix": "lglass:",
	"robots.txt": None
}

def get_config():
	config = DEFAULT_CONFIG
	config.update(bottle.request.environ.get("lglass-web.config", {}))
	if "LGLASS_WEB_CFG" in os.environ:
		try:
			with open(os.environ["LGLASS_WEB_CFG"]) as fh:
				config.update(json.load(fh))
		except (FileNotFoundError, ValueError):
			pass

	return config

def with_config(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		config = bottle.request.app.config.get("lglass.config")
		if config is None:
			config = get_config()
			bottle.request.app.config["lglass.config"] = config
		return func(config=config, *args, **kwargs)
	return wrapper
	
