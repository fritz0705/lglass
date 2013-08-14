# coding: utf-8

import re

import lglass.rpsl
import netaddr

def roa_record(route, table):
	network = netaddr.IPNetwork(route.primary_key)
	autnum = route["origin"].replace("AS", "")

	if not re.match("^[0-9]+$", autnum):
		raise ValueError()

	return "add roa {network} max {max} as {autnum} table {table}".format(
		network=str(network),
		max=network.prefixlen,
		autnum=autnum,
		table=table
	)

def roa_table(routes, table):
	for route in routes:
		try:
			yield roa_record(route, table)
		except (netaddr.core.AddrFormatError, ValueError):
			pass

