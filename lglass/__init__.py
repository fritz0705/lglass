# coding: utf-8

import json
import lglass.bird
import lglass.rpsl

config = json.load(open("lglass.json"))
bird_client = bird.Bird(birdc=config["programs"]["birdc"], default_table="dn42")
registry = rpsl.Database(config["registry"])

