# coding: utf-8

# XXX This code is so horrible, don't read it

import lglass.rpsl
import netaddr
import time
import traceback

def rdns_domain(network):
	if network.version == 4:
		return ".".join(map(str, reversed(network.ip.words[:network.prefixlen // 8]))) + ".in-addr.arpa"
	elif network.version == 6:
		return ".".join(map(str, reversed(list("".join(hex(n)[2:].rjust(4, "0") for n in network.ip.words))[:network.prefixlen // 4]))) + ".ip6.arpa"

def delegation(domain, nameserver):
	nameserver, *trash = nameserver.split()
	return "{domain}. IN NS {nserver}.".format(
		domain=domain,
		nserver=nameserver)

def rdns_delegation(network, nameserver):
	return delegation(rdns_domain(network), nameserver)

rdns4_delegation = rdns_delegation
rdns6_delegation = rdns_delegation

def glue(domain, addr):
	if addr.version == 4:
		return "{ns}. IN A {glue}".format(ns=domain, glue=str(addr))
	elif addr.version == 6:
		return "{ns}. IN AAAA {glue}".format(ns=domain, glue=str(addr))

def generate_delegation(dns, with_glue=True):
	""" Generate a valid DNS delegation to the given dns object. This function
	may generate glue records if with_glue == True. """
	result = []

	for _, nserver in dns.get("nserver"):
		ns, *glues = nserver.split()
		result.append(delegation(dns.primary_key, ns))
		if with_glue is False:
			glues = []
		for _glue in glues:
			if not ns.endswith(dns.primary_key):
				continue
			try:
				_glue = netaddr.IPAddress(_glue)
				result.append(glue(ns, _glue))
			except:
				pass
	
	return result

def generate_rdns4_delegation(net, inetnum):
	result = []

	networks = lglass.rpsl.inetnum_cidrs(inetnum)

	for network in networks:
		if network not in net:
			continue
		for subnet in network.subnet(net.prefixlen // 8 * 8 + 8):
			for _, nserver in inetnum.get("nserver"):
				result.append(rdns_delegation(subnet, nserver))
	
	return result

def generate_rdns6_delegation(net, inet6num):
	result = []
	
	networks = lglass.rpsl.inetnum_cidrs(inet6num)

	for network in networks:
		if network not in net:
			continue
		for subnet in network.subnet(net.prefixlen // 4 * 4 + 4):
			for _, nserver in inet6num.get("nserver"):
				result.append(rdns_delegation(subnet, nserver))
	
	return result

def generate_soa(domain, master, email, serial=None, refresh=86400, retry=7200,
		expire=3600000, ttl=172800):
	""" Useful utility to generate a RIPE-NCC-compilant SOA record for defined
	domain. Required fields are the domain, the master name server, the email
	address in zonefile format. Additional fields are the serial, refresh time,
	retry time, expire time and minimum ttl. If the serial is ommitted, then
	this function will generate a unique serial based on the current time. """
	if serial is None:
		serial = int(time.time())
	
	return "{domain}. IN SOA {master}. {email}. {serial} {refresh} {retry} {expire} {ttl}".format(
		domain=domain,
		master=master,
		email=email,
		serial=serial,
		refresh=refresh,
		retry=retry,
		expire=expire,
		ttl=ttl)

def generate_zone(zone, domains, soa=None, nameservers=[]):
	""" Generate fully compilant zone for given domains, which need delegation. """

	result = []

	if soa is not None:
		if isinstance(soa, tuple):
			soa = generate_soa(zone, *soa)
		elif isinstance(soa, dict):
			soa = generate_soa(zone, **soa)
		result.append(soa)

	for nameserver in nameservers:
		result.append(delegation(zone, nameserver))
	
	for domain in domains:
		if not domain.primary_key.endswith("." + zone):
			result.append("; {domain} is out-of-zone".format(domain=domain.primary_key))
			continue
		
		result.append("; {domain}".format(domain=domain.primary_key))
		result.extend(generate_delegation(domain))
	
	return result

def generate_rdns4_zone(network, inetnums, soa=None, nameservers=[]):
	result = []

	zone = rdns_domain(network)
	delegated_len = network.prefixlen // 8 * 8 + 8

	if soa is not None:
		if isinstance(soa, tuple):
			soa = generate_soa(zone, *soa)
		elif isinstance(soa, dict):
			soa = generate_soa(zone, **soa)
		result.append(soa)
	
	for nameserver in nameservers:
		result.append(delegation(zone, nameserver))
	
	for inetnum in inetnums:
		result.append("; {inetnum}".format(inetnum=inetnum.primary_key))
		try:
			result.extend(generate_rdns4_delegation(network, inetnum))
		except:
			traceback.print_exc()
			result.append("; Exception occured.")

	return result

def generate_rdns6_zone(network, inet6nums, soa=None, nameservers=[]):
	result = []

	zone = rdns_domain(network)
	delegated_len = network.prefixlen // 4 * 4 + 4

	if soa is not None:
		if isinstance(soa, tuple):
			soa = generate_soa(zone, *soa)
		elif isinstance(soa, dict):
			soa = generate_soa(zone, **soa)
		result.append(soa)
	
	for nameserver in nameservers:
		result.append(delegation(zone, nameserver))
	
	for inet6num in inet6nums:
		result.append("; {inet6num}".format(inet6num=inet6num.primary_key))
		try:
			result.extend(generate_rdns6_delegation(network, inet6num))
		except:
			traceback.print_exc()
			result.append("; Exception occured.")
	
	return result

