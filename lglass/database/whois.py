# coding: utf-8

import socket

import lglass.rpsl
import lglass.database.base

@lglass.database.base.register
class WhoisClientDatabase(lglass.database.base.Database):
	""" Simple blocking whois client database """

	def __init__(self, hostspec):
		self.hostspec = hostspec
	
	def get(self, type, primary_key):
		try:
			return self.find(primary_key, types=[type], flags="-r")[-1]
		except IndexError:
			raise KeyError(type, primary_key)

	def find(self, primary_key, types=None, flags=None):
		send_buffer = b""
		recv_buffer = b""

		if types is not None:
			send_buffer += "-T {types} ".format(types=",".join(types)).encode()
		if flags is not None:
			send_buffer += flags.encode()
			send_buffer += b" "
		send_buffer += "{key}".format(key=primary_key).encode()
		send_buffer += b"\r\n"

		with socket.create_connection(self.hostspec) as sock:
			while len(send_buffer):
				sent = sock.send(send_buffer)
				send_buffer = send_buffer[sent:]
			while True:
				recvd = sock.recv(1024)
				if not len(recvd):
					break
				recv_buffer += recvd

		lines = recv_buffer.decode().splitlines()
		lines_iter = iter(lines)

		objs = []

		while True:
			obj = lglass.rpsl.Object.from_iterable(lines_iter, pragmas={
				"stop-at-empty-line": True
			})
			if not obj:
				break
			objs.append(obj)

		return objs

	def list(self):
		raise NotImplementedError("list() is not supported for WhoisClientDatabase")

	def save(self):
		raise NotImplementedError("save() is not supported for WhoisClientDatabase")

	def delete(self):
		raise NotImplementedError("delete() is not supported for WhoisClientDatabase")

	@classmethod
	def from_url(cls, url):
		return cls((url.hostname, url.port if url.port else 43))

@lglass.database.base.register
class RIPEDatabase(WhoisClientDatabase):
	def __init__(self, hostspec=None):
		if hostspec is None:
			hostspec = ("whois.ripe.net", 43)
		WhoisClientDatabase.__init__(self, hostspec)

	def find(self, primary_key, types=None, flags=None):
		if flags is not None:
			flags = "-B " + flags
		else:
			flags = "-B"
		return WhoisClientDatabase.find(self, primary_key, types, flags)
	
	def schema(self, type):
		results = self.find(type, flags="-t")
		if len(results) == 0:
			raise KeyError("schema({})".format(type))
		return lglass.rpsl.RIPESchemaObject(results[0])

	@classmethod
	def from_url(cls, url):
		return cls()

