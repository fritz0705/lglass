# coding: utf-8

import lglass.database
import asyncore
import traceback

class WhoisHandler(object):
	def __init__(self, database):
		self.database = database
	
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
		for req in requested:
			response.append("% Query {}\n\n".format(req))

			if "e" not in flags:
				objects = self.database.find(req)
			else:
				req = req.split("~", 1)
				objects = [self.database.get(*req)]

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
		self.line = b""

	def handle_read(self):
		self.line += self.recv(1)
		if b"\n" in self.line:
			self.line = self.line.decode().split("\n")[0].strip()
			try:
				result = handler.handle(self.line).encode()
			except:
				traceback.print_exc()
				self.send("% An error occured while handling the query\n")
				send.close()

			self.send(result)
			self.close()

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
	argparser.add_argument("--host", "-H", type=str, default="0.0.0.0")
	argparser.add_argument("--port", "-P", type=int, default=4343)
	argparser.add_argument("--db", "-D", type=str, default=".")
	argparser.add_argument("--no-cache", action="store_true", default=False)
	argparser.add_argument("--user", "-u")
	argparser.add_argument("--group", "-g")
	argparser.add_argument("--pidfile", "-p", type=str)

	args = argparser.parse_args()

	db = lglass.database.FileDatabase(args.db)
	db = lglass.database.CIDRDatabase(db)
	if not args.no_cache:
		db = lglass.database.CachedDatabase(db)

	handler = WhoisHandler(db)

	def sighup(sig, frame):
		if not args.no_cache:
			print("Flush query cache", file=sys.stderr)
			db.flush()
	
	for sig in [signal.SIGHUP, signal.SIGUSR1]:
		signal.signal(sig, sighup)

	if args.pidfile:
		with open(args.pidfile, "w") as f:
			f.write(str(os.getpid()))

	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind((args.host, args.port))
	sock.listen(5)

	if args.user:
		drop_priv(args.user, args.group)

	WhoisdServer(sock, handler)
	asyncore.loop()

