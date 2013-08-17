# coding: utf-8

import lglass.database
import asyncore
import traceback
import argparse

DEFAULT_HELP = (
"""NAME
    whois query server

DESCRIPTION
    The following options are available:
    
    -x, --exact
          Performs an exact search

    -T (comma separated list of object types with no white space)
          Returns only objects with a given type

    -t
          Performs a search for schemas
""")

DEFAULT_VERSION = (
"""lglass - Registry service package
(c) 2013 Fritz Conrad Grimpen

http://github.com/fritz0705/lglass
""")

class WhoisHandler(object):
	preamble = None
	help_message = DEFAULT_HELP
	version_message = DEFAULT_VERSION

	def __init__(self, database, keys=[], **kwargs):
		self.database = database
		self.keys = frozenset(keys)

		self.__dict__.update(kwargs)

	def _schema_lookup(self, request, arguments, flags):
		try:
			schema = self.database.schema(request)
			return [schema]
		except KeyError:
			return []

	def _objs_lookup(self, request, arguments, flags):
		filters = []
		post_filters = []
		objects = []

		if "-T" in arguments:
			types = arguments["-T"].split(",")
			post_filters.append(lambda obj: obj.type in types)
		if "x" in flags:
			filters.append(lambda spec: spec[1] == request)

		if filters:
			objects = self.database.list()
			for _filter in filters:
				objects = filter(_filter, objects)
			objects = [self.database.get(*spec) for spec in objects]
		else:
			objects = self.database.find(request)

		for post_filter in post_filters:
			objects = filter(post_filter, objects)

		return objects
	
	def handle(self, request):
		""" This method handles a simple WHOIS request and returns a plain response.
		The request is given as string and will be tokenzied for further
		processing. """

		request = request.split()

		flags = set()
		arguments = {}
		requested = []

		req_iter = iter(request)
		for req in req_iter:
			if req in ["-T", "-k", "-q"]:
				arguments[req] = next(req_iter)
			elif req in ["-x", "-t"]:
				flags.add(req[1:])
			else:
				requested.append(req)

		response = []
		if self.preamble is not None:
			response.append("% {}\n\n".format(self.preamble))

		if arguments.get("-q") == "version":
			requested.append("--version")
		elif arguments.get("-q") == "types":
			requested.append("--types")

		for req in requested:
			response.append("% Query {}\n\n".format(req))

			objects = []

			if req in ["help", "--help"]:
				help = "% " + self.help_message.replace("\n", "\n% ")
				response.append(help)
				response.append("\n\n")
				continue
			elif req == "--types":
				response.append("\n".join(self.database.object_types))
				response.append("\n\n")
				continue
			elif req == "--version":
				version_msg = "% " + self.version_message.replace("\n", "\n% ")
				response.append(version_msg)
				response.append("\n\n")
				continue

			if "t" in flags:
				objects = self._schema_lookup(req, arguments, flags)
			else:
				objects = self._objs_lookup(req, arguments, flags)

			for obj in objects:
				response.append("% Object {}\n\n".format(obj.spec))
				response.append(obj.pretty_print())
				response.append("\n")
			if not objects:
				response.append("% No matching objects found\n\n")

		return "".join(response)

class WhoisdHandler(asyncore.dispatcher):
	def __init__(self, sock, handler):
		asyncore.dispatcher_with_send.__init__(self, sock)

		self.handler = handler

		self.__readable = True
		self.recv_buffer = b""
		self.send_buffer = b""

	def readable(self):
		return self.__readable
	
	def writable(self):
		return len(self.send_buffer) > 0

	def handle_write(self):
		sent = self.send(self.send_buffer)
		self.send_buffer = self.send_buffer[sent:]

		if len(self.send_buffer) == 0:
			self.close()

	def handle_read(self):
		self.recv_buffer += self.recv(1024)
		if b"\n" in self.recv_buffer:
			self.__readable = False
			line = self.recv_buffer.split(b"\n")[0].strip()
			try:
				self.send_buffer = self.handler.handle(line.decode()).encode()
			except:
				self.send_buffer += b"% An error occured while handling the query:\n"
				exception = traceback.format_exc()
				for line in exception.splitlines():
					self.send_buffer += b"%   " + line.encode() + b"\n"

class WhoisdServer(asyncore.dispatcher):
	accepting = True

	def __init__(self, sock, handler):
		asyncore.dispatcher.__init__(self, sock)
		self.handler = handler
	
	def handle_accepted(self, sock, addr):
		WhoisdHandler(sock, self.handler)

if __name__ == '__main__':
	main()

def main():
	import argparse
	import socket
	import signal
	import sys
	import os
	import pwd
	import json

	def drop_priv(user, group):
		try:
			pw = pwd.getpwnam(user)
		except KeyError:
			pw = pwd.getpwuid(int(user))

		uid, gid = pw.pw_uid, pw.pw_gid

		if group:
			try:
				gr = grp.getgrnam(group)
			except KeyError:
				gr = grp.getgrgid(int(group))

			gid = grp.gid

		os.setgid(gid)
		os.setuid(uid)

	argparser = argparse.ArgumentParser(description="Simple whois server")
	argparser.add_argument("--config", "-c",
		help="Path to configuration file")
	argparser.add_argument("--host", "-H", type=str,
		help="Address to bind")
	argparser.add_argument("--port", "-P", type=int,
		help="Port to bind")
	argparser.add_argument("--db", "-D", type=str,
		help="Path to Whois database")
	argparser.add_argument("--no-cache", action="store_false", dest="cache",
		help="Disable caching layer and serve requests directly from database")
	argparser.add_argument("--user", "-u",
		help="Drop priviliges after start and set uid")
	argparser.add_argument("--group", "-g",
		help="Set group")
	argparser.add_argument("--pidfile", "-p", type=str,
		help="Write PID to file after startup")
	argparser.add_argument("--preamble",
		help="Preamble for any whois response")
	argparser.add_argument("--key", "-k", action='append',
		help="Add key to transfer keys")
	argparser.add_argument("-4", dest="protocol", action='store_const', const=4,
		help="Operate in IPv4 mode")
	argparser.add_argument("-6", dest="protocol", action='store_const', const=6,
		help="Operate in IPv6 mode")

	args = argparser.parse_args()

	config = {
		"listen.host": "::",
		"listen.port": 4343,
		"listen.protocol": 6,

		"database.path": ".",
		"database.caching": True,
		"database.caching.type": "memory",
		"database.caching.url": "redis://localhost:6379/0",
		"database.caching.timeout": 600,
		"database.caching.prefix": "lglass:",
		"database.cidr": True,
		"database.inverse": True,
		"database.inverse.types": None,

		"messages.preamble": "This is a generic whois query service.",
		"messages.help": DEFAULT_HELP,

		"process.user": None,
		"process.group": None,
		"process.pidfile": None,
	}

	if args.config:
		with open(args.config) as fh:
			config.update(json.load(fh))
	
	for value, destination in [
			(args.host,     "listen.host"),
			(args.port,     "listen.port"),
			(args.protocol, "listen.protocol"),
			(args.db,       "database.path"),
			(args.cache,    "database.caching"),
			(args.preamble, "messages.preamble"),
			(args.user,     "process.user"),
			(args.group,		"process.group"),
			(args.pidfile,	"process.pidfile")
		]:
		if value is not None:
			config[destination] = value

	db = lglass.database.FileDatabase(config["database.path"])
	if config["database.cidr"]:
		db = lglass.database.CIDRDatabase(db)
	if config["database.inverse"]:
		db = lglass.database.InverseDatabase(db)
		if config["database.inverse.types"]:
			db.inverse_type_filter = lambda key: key in config["database.inverse.types"]
	if config["database.caching"]:
		if config["database.caching.type"] == "redis":
			db = lglass.database.RedisDatabase(db,
				config["database.caching.url"],
				timeout=config["database.caching.timeout"],
				prefix=config["database.caching.prefix"])
		else:
			db = lglass.database.CachedDatabase(db)

	handler = WhoisHandler(db,
		preamble=config["messages.preamble"],
		help_message=config["messages.help"],
		keys=[])

	def sighup(sig, frame):
		if config["database.caching"]:
			print("Flush query cache", file=sys.stderr)
			db.flush()
	
	for sig in [signal.SIGHUP, signal.SIGUSR1]:
		signal.signal(sig, sighup)

	if config["process.pidfile"]:
		with open(config["process.pidfile"], "w") as f:
			f.write(str(os.getpid()) + "\n")

	if config["listen.protocol"] == 4:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	elif config["listen.protocol"] == 6:
		sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind((config["listen.host"], config["listen.port"]))
	sock.listen(5)

	if config["process.user"]:
		drop_priv(config["process.user"], config["process.group"])

	WhoisdServer(sock, handler)
	asyncore.loop()

