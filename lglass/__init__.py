# coding: utf-8

import json
import lglass.bird
import lglass.rpsl

config = json.load(open("lglass.json"))
bird_client = bird.Bird(
	birdc=config["programs"]["birdc"],
	default_table=config["bird"]["table"],
	route_filter=bird.BGPRoute.type_filter
)
registry = rpsl.Database(config["registry"])

