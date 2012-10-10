# coding: utf-8

import bottle
import jinja2
import lglass

config = lglass.config
bird_client = lglass.bird_client

application = bottle.Bottle()
jinja2_env = jinja2.Environment(loader=jinja2.PackageLoader("lglass.web", "templates"))

import lglass.web.home
import lglass.web.registry
import lglass.web.lg
import lglass.web.search

