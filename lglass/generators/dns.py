# coding: utf-8

# XXX This code is so horrible, don't read it

import lglass.rpsl
import netaddr
import time

def delegation(domain, nameserver):
	nameserver, *trash = nameserver.split()
	return "{domain}. IN NS {nserver}.".format(
		domain=domain,
		nserver=nameserver)

def rdns4_delegation(network, nameserver):
	""" Generate delegating resource record for a given IPv4 network and one
	nameserver. This function does not check whether there is a valid rDNS
	representation for the given network prefix length. """
	return delegation(
		".".join(map(str, reversed(
			network.ip.words[:network.prefixlen // 8]
		))) + ".in-addr.arpa", nameserver)

def rdns6_delegation(network, nameserver):
	""" Generate delegating resource record for a given IPv6 network and one
	nameserver. This function does not check whether there is a valid rDNS
	representation for the given network prefix length. """
	return delegation(
		".".join(map(str, reversed(
			list("".join(hex(n)[2:].rjust(4, "0") for n in network.ip.words))[:network.prefixlen // 4]
		))) + ".ip6.arpa",
		nameserver)

def rdns_delegation(network, nameserver):
	if network.version == 4:
		return rdns4_delegation(network, nameserver)
	elif network.version == 6:
		return rdns6_delegation(network, nameserver)

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

def generate_rdns4_delegation(inetnum):
	result = []

	networks = netaddr.IPRange(*[ipr.strip() for ipr in inetnum.primary_key.split("-", 1)])
	networks = networks.cidrs()

	for network in networks:
		if network.prefixlen > 24:
			continue
		elif network.prefixlen % 8 != 0:
			subnets = network.subnet(network.prefixlen // 8 * 8 + 8)
			for subnet in subnets:
				result.extend(rdns4_delegation(subnet, ns) for _, ns in inetnum.get("nserver"))
		else:
			result.extend(rdns4_delegation(network, ns) for _, ns in inetnum.get("nserver"))
	
	return result

def generate_rdns6_delegation(inet6num):
	result = []

	networks = netaddr.IPRange(*[ipr.strip() for ipr in inet6num.primary_key.split("-", 1)])
	networks = networks.cidrs()

	for network in networks:
		if network.prefixlen % 4 != 0:
			subnets = network.subnet(network.prefixlen // 4 * 4 + 4)
			for subnet in subnets:
				result.extend(rdns6_delegation(subnet, ns) for _, ns in inet6num.get("nserver"))
		else:
			result.extend(rdns6_delegation(network, ns) for _, ns in inet6num.get("nserver"))
	
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

