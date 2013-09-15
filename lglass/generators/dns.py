# coding: utf-8

import lglass.rpsl
import lglass.dns
import netaddr
import time

def rdns_domain(network):
	if network.version == 4:
		return ".".join(map(str, reversed(network.ip.words[:network.prefixlen // 8]))) + ".in-addr.arpa"
	elif network.version == 6:
		return ".".join(map(str, reversed(list("".join(hex(n)[2:].rjust(4, "0") for n in network.ip.words))[:network.prefixlen // 4]))) + ".ip6.arpa"

def comment(txt):
	return "; {}".format(str(txt))

def delegation(domain, nameserver):
	nameserver, *_ = nameserver.split()
	return lglass.dns.ResourceRecord(domain, "NS", lglass.dns.absolute(nameserver))

def rdns_delegation(network, nameserver):
	return delegation(rdns_domain(network), nameserver)

rdns4_delegation = rdns_delegation
rdns6_delegation = rdns_delegation

def glue(domain, addr):
	if addr.version == 4:
		return lglass.dns.ResourceRecord(domain, "A", addr)
	elif addr.version == 6:
		return lglass.dns.ResourceRecord(domain, "AAAA", addr)

def generate_delegation(dns, with_glue=True):
	""" Generate a valid DNS delegation to the given dns object. This function
	may generate glue records if with_glue == True. """
	seen_servers = set()
	for _, nserver in dns.get("nserver"):
		ns, *glues = nserver.split()
		if ns not in seen_servers:
			seen_servers.add(ns)
			yield delegation(dns.primary_key, ns)
		if with_glue is False:
			glues = []
		for _glue in glues:
			if not ns.endswith(dns.primary_key):
				continue
			try:
				_glue = netaddr.IPAddress(_glue)
				yield glue(ns, _glue)
			except:
				pass
	if with_glue is True:
		for _, glueval in dns.get("glue"):
			domain, *glues = glueval.split()
			if not domain.endswith(dns.primary_key):
				continue
			for _glue in glues:
				try:
					_glue = netaddr.IPAddress(_glue)
					yield glue(ns, _glue)
				except:
					pass

def generate_rdns4_delegation(subnet, inetnum):
	for _, nserver in inetnum.get("nserver"):
		yield rdns_delegation(subnet, nserver)

generate_rdns6_delegation = generate_rdns4_delegation

def generate_soa(domain, master, email, serial=None, refresh=86400, retry=7200,
		expire=3600000, ttl=172800):
	""" Useful utility to generate a RIPE-NCC-compilant SOA record for defined
	domain. Required fields are the domain, the master name server, the email
	address in zonefile format. Additional fields are the serial, refresh time,
	retry time, expire time and minimum ttl. If the serial is ommitted, then
	this function will generate a unique serial based on the current time. """
	if serial is None:
		serial = int(time.time())
	
	return lglass.dns.ResourceRecord(domain, "SOA", lglass.dns.absolute(master),
		lglass.dns.email(email), serial, refresh, retry, expire, ttl)

def generate_zone(zone, domains, soa=None, nameservers=[]):
	""" Generate fully compilant zone for given domains, which need delegation. """

	if soa is not None:
		if isinstance(soa, tuple):
			soa = generate_soa(zone, *soa)
		elif isinstance(soa, dict):
			soa = generate_soa(zone, **soa)
		yield soa

	for nameserver in nameservers:
		yield delegation(zone, nameserver)
	
	for domain in domains:
		if not domain.primary_key.endswith("." + zone):
			yield "; {domain} is out-of-zone".format(domain=domain.primary_key)
			continue
		
		yield "; {domain}".format(domain=domain.primary_key)
		yield from generate_delegation(domain)

def generate_rdns4_zone(network, inetnums, soa=None, nameservers=[]):
	if network.prefixlen % 8:
		raise ValueError("Network prefixlen must be a multiple of 8, got {}".format(network.prefixlen))

	zone = rdns_domain(network)
	delegated_len = network.prefixlen // 8 * 8 + 8

	if soa is not None:
		if isinstance(soa, tuple):
			soa = generate_soa(zone, *soa)
		elif isinstance(soa, dict):
			soa = generate_soa(zone, **soa)
		yield soa
	
	for nameserver in nameservers:
		yield delegation(zone, nameserver)

	delegations = {}

	for inetnum in inetnums:
		for net in lglass.rpsl.inetnum_cidrs(inetnum):
			if net not in network:
				continue

			for subnet in net.subnet(delegated_len):
				if subnet not in delegations:
					delegations[subnet] = inetnum

				range1, range2 = map(lglass.rpsl.inetnum_range, (inetnum, delegations[subnet]))
				if range1 > range2:
					delegations[subnet] = inetnum
	
	for subnet, inetnum in delegations.items():
		yield from generate_rdns4_delegation(subnet, inetnum)

def generate_rdns6_zone(network, inet6nums, soa=None, nameservers=[]):
	if network.prefixlen % 4:
		raise ValueError("Network prefixlen must be a multiple of 4, got {}".format(network.prefixlen))

	zone = rdns_domain(network)

	if soa is not None:
		if isinstance(soa, tuple):
			soa = generate_soa(zone, *soa)
		elif isinstance(soa, dict):
			soa = generate_soa(zone, **soa)
		yield soa
	
	for nameserver in nameservers:
		yield delegation(zone, nameserver)

	delegations = {}

	for inetnum in inet6nums:
		for net in lglass.rpsl.inetnum_cidrs(inetnum):
			if net not in network:
				continue

			delegated_len = net.prefixlen // 4 * 4 + 4 if net.prefixlen % 4 else net.prefixlen

			for subnet in net.subnet(delegated_len):
				if subnet not in delegations:
					delegations[subnet] = inetnum

				range1, range2 = map(lglass.rpsl.inetnum_range, (inetnum, delegations[subnet]))
				if range1 > range2:
					delegations[subnet] = inetnum
	
	for subnet, inetnum in delegations.items():
		yield from generate_rdns6_delegation(subnet, inetnum)

