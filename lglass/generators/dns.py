# coding: utf-8

import lglass.rpsl
import netaddr
import time

def generate_delegation(dns, with_glue=True):
	""" Generate a valid DNS delegation to the given dns object. This function
	may generate glue records if with_glue == True. """
	result = []

	for _, nserver in dns.get("nserver"):
		ns, *glues = nserver.split()
		result.append("{domain}. IN NS {nserver}.".format(domain=dns.primary_key,
			nserver=ns))
		if with_glue is False: glues = []
		for glue in glues:
			if not ns.endswith(dns.primary_key):
				continue
			try:
				glue = netaddr.IPAddress(glue)
				if glue.version == 4:
					result.append("{ns}. IN A {glue}.".format(ns=ns, glue=str(glue)))
				elif glue.version == 6:
					result.append("{ns}. IN AAAA {glue}.".format(ns=ns, glue=str(glue)))
			except:
				pass
	
	return result

def generate_rdns4_delegation(inetnum):
	result = []

	networks = netaddr.IPRange(*[ipr.strip() for ipr in inetnum.primary_key.split("-", 1)])
	networks = networks.cidrs()

	for network in networks:
		if network.prefixlen % 8 != 0:
			continue

		domain = network.ip.words[:network.prefixlen // 8]
		domain = reversed(domain)
		domain = ".".join(str(w) for w in domain) + ".in-addr.arpa"

		for _, nserver in inetnum.get("nserver"):
			ns, *glues = nserver.split()
			result.append("{domain}. IN NS {nserver}.".format(
				domain=domain, nserver=ns))
	
	return result

def generate_rdns6_delegation(inet6num):
	result = []

	networks = netaddr.IPRange(*[ipr.strip() for ipr in inet6num.primary_key.split("-", 1)])
	networks = networks.cidrs()

	for network in networks:
		if network.prefixlen % 4 != 0:
			continue

		byte_s = list("".join(hex(n)[2:].rjust(4, "0") for n in network.ip.words))
		byte_s = byte_s[:network.prefixlen // 4]
		byte_s = reversed(byte_s)
		domain = ".".join(byte_s) + ".ip6.arpa"

		for _, nserver in inet6num.get("nserver"):
			ns, *glues = nserver.split()
			result.append("{domain}. IN NS {nserver}.".format(domain=domain,
				nserver=ns))
	
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
	
	return "{domain}. IN SOA {master} {email} {serial} {refresh} {retry} {expire} {ttl}".format(
		domain=domain,
		master=master,
		email=email,
		serial=serial,
		refresh=refresh,
		retry=retry,
		expire=expire,
		ttl=ttl)

