# coding: utf-8

import lglass.database
import asyncore
import traceback

class WhoisHandler(object):
	def __init__(self, database, preamble=None, keys=[]):
		self.database = database
		self.preamble = preamble
		self.keys = set(keys)
	
	def handle(self, request):
		""" This method handles a simple WHOIS request and returns a plain response.
		The request is given as string and will be tokenzied for further
		processing. """

		request = request.split(" ")

		requested = []
		flags = set()
		for req in request:
			if req[0] == '-':
				flags.update(set(req[1]))
				continue

			requested.append(req)

		response = []
		if self.preamble is not None:
			response.append("% {}\n\n".format(self.preamble))

		for req in requested:
			response.append("% Query {} [{}]\n\n".format(req, "".join(flags)))

			if "a" in flags:
				# whois database transfer
				# don't use it!
				if req not in self.keys:
					response.append("% Access not authorized\n\n")
					continue

				objects = [self.database.get(*ls) for ls in self.database.list()]
			elif "x" in flags:
				req = req.split("+", 1)
				if len(req) == 2:
					objects = [self.database.get(*req)]
				else:
					req = req[0]
					objects = [self.database.get(*ls) for ls in self.database.list() if ls[1] == req]
			else:
				objects = self.database.find(req)

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
	import argparse
	import socket
	import signal
	import sys
	import os
	import pwd

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
	argparser.add_argument("--host", "-H", type=str, default="0.0.0.0",
		help="Address to bind")
	argparser.add_argument("--port", "-P", type=int, default=4343,
		help="Port to bind")
	argparser.add_argument("--db", "-D", type=str, default=".",
		help="Path to Whois database")
	argparser.add_argument("--no-cache", action="store_true", default=False,
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

	db = lglass.database.FileDatabase(args.db)
	db = lglass.database.CIDRDatabase(db)
	if not args.no_cache:
		db = lglass.database.CachedDatabase(db)

	handler = WhoisHandler(db, preamble=args.preamble, keys=(args.key or []))

	def sighup(sig, frame):
		if not args.no_cache:
			print("Flush query cache", file=sys.stderr)
			db.flush()
	
	for sig in [signal.SIGHUP, signal.SIGUSR1]:
		signal.signal(sig, sighup)

	if args.pidfile:
		with open(args.pidfile, "w") as f:
			f.write(str(os.getpid()))

	if args.protocol == 4 or args.protocol is None:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	elif args.protocol == 6:
		sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind((args.host, args.port))
	sock.listen(5)

	if args.user:
		drop_priv(args.user, args.group)

	WhoisdServer(sock, handler)
	asyncore.loop()

