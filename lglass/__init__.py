# coding: utf-8

import bottle
import json

config = json.load(open("lglass.json"))

import lglass.graphviz
