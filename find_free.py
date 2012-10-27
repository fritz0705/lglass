#!/usr/bin/env python3
# coding: utf-8

import netaddr
import lglass
import sys
from progress.bar import Bar
from progress.spinner import Spinner

routes = lglass.bird.Parser().parse_routes(sys.stdin.read())
dn42_native = netaddr.IPNetwork("172.22.0.0/15")

routes = filter(lambda route: route.network in dn42_native, routes)
routes = sorted(routes, key=lambda route: route.network)

def window(iterable, size):
	win = []
	for e in iterable:
		if len(win) < size:
			win.append(e)
			continue
		yield win
		win = win[1:] + [e]

def flatten(iterable, levels=1):
	return [item for sublist in iterable for item in sublist]

class FancyBar(Bar):
	fill = "#"
	suffix = "%(index)d/%(max)d %(percent)d%% %(avg)f/item"
	bar_prefix = " ["
	bar_suffix = "] "

route_addresses = []
bar = FancyBar("Extracting addresses", max=len(routes))

for route in routes:
	route_addresses.extend(map(netaddr.IPAddress, route.network.subnet(32)))
	bar.next()

bar.finish()

addresses = {}
for address in map(netaddr.IPAddress, dn42_native.subnet(32)):
	addresses[address] = address

bar = FancyBar("Creating delta", max=len(route_addresses))

for route_address in route_addresses:
	try:
		del addresses[route_address]
		#addresses.remove(route_address)
	except KeyError:
		pass
	bar.next()

bar.finish()
addresses = list(addresses.keys())
addresses = sorted(addresses)

bar = FancyBar("Merging addresses", max=len(addresses))
ranges = []
current_range = None
for address in addresses:
	if current_range:
		if current_range.last + 1 == int(address):
			current_range = netaddr.IPRange(current_range.first, address)
		else:
			ranges.append(current_range)
			current_range = None
	
	if not current_range:
		current_range = netaddr.IPRange(address, address)
	bar.next()
bar.finish()

ranges = map(lambda r: r.cidrs(), ranges)
print(list(ranges))
