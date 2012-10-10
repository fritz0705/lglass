# coding: utf-8

import json
import lglass.bird
import lglass.rpsl

config = None
bird_client = None
registry = None

try:
	with open("lglass.json") as f:
		config = json.load(f)
	bird_client = bird.Client(
		birdc=config["programs"]["birdc"],
		default_table=config["bird"]["table"],
		route_filter=bird.BGPRoute.type_filter
	)
	registry = rpsl.Database(config["registry"])
except:
	pass
