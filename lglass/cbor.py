# coding: utf-8

import flynn
import netaddr

import lglass.route
import lglass.rpsl

class Encoder(flynn.encoder.Encoder):
	def encode(self, object):
		if isinstance(object, lglass.route.Route):
			self.encode_route(object)
		elif isinstance(object, netaddr.IPNetwork):
			self.encode_ipnetwork(object)
		elif isinstance(object, netaddr.IPAddress):
			self.encode_ipaddress(object)
		elif isinstance(object, lglass.rpsl.Object):
			self.encode_object(object)
		elif isinstance(object, tuple):
			self.encode_list(object)
		elif isinstance(object, lglass.route.RoutingTable):
			self.encode_routingtable(object)
		else:
			flynn.encoder.Encoder.encode(self, object)
	
	def encode_route(self, route):
		self.encode_tagging(flynn.Tagging(33000, [
			route.prefix,
			list(route.nexthop),
			route.metric,
			route.annotations]))
	
	def encode_ipnetwork(self, ipnetwork):
		self.encode_tagging(flynn.Tagging(33001, [
			bytes(ipnetwork.ip.packed), ipnetwork.prefixlen]))

	def encode_ipaddress(self, ipaddress):
		self.encode_tagging(flynn.Tagging(33002, ipaddress.packed))
	
	def encode_object(self, object):
		self.encode_tagging(flynn.Tagging(33003, object.data))

	def encode_routingtable(self, routingtable):
		self.encode_tagging(flynn.Tagging(33004, routingtable.routes))

class Decoder(flynn.decoder.StandardDecoder):
	def __init__(self, *args, **kwargs):
		flynn.decoder.StandardDecoder.__init__(self, *args, **kwargs)
		self.register_tagging(33000, self.decode_route_tag)
		self.register_tagging(33001, self.decode_ipnetwork_tag)
		self.register_tagging(33002, self.decode_ipaddress_tag)
		self.register_tagging(33003, self.decode_object_tag)
		self.register_tagging(33004, self.decode_routingtable_tag)

	def decode_route_tag(self, tag, object):
		return lglass.route.Route(object[0], tuple(object[1]), object[2], object[3])

	def decode_ipnetwork_tag(self, tag, object):
		return netaddr.IPNetwork((int.from_bytes(object[0], "big"), object[1]))

	def decode_ipaddress_tag(self, tag, object):
		return netaddr.IPAddress(int.from_bytes(object, "big"))

	def decode_object_tag(self, tag, object):
		return lglass.rpsl.Object(object)

	def decode_routingtable_tag(self, tag, object):
		return lglass.route.RoutingTable(object)

def dump(*args, **kwargs):
	kwargs.setdefault("cls", Encoder)
	return flynn.dump(*args, **kwargs)

def dumps(*args, **kwargs):
	kwargs.setdefault("cls", Encoder)
	return flynn.dumps(*args, **kwargs)

def load(*args, **kwargs):
	kwargs.setdefault("cls", Decoder)
	return flynn.load(*args, **kwargs)

def loads(*args, **kwargs):
	kwargs.setdefault("cls", Decoder)
	return flynn.loads(*args, **kwargs)

