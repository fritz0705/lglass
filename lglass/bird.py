# coding: utf-8

import subprocess

import netaddr

import lglass.route

class BirdClient(object):
	def __init__(self, executable="birdc"):
		self.executable = executable
	
	def send(self, command, raw=False):
		argv = [self.executable]
		if raw:
			argv.append("-v")
		if isinstance(command, str):
			argv.extend(command.split())
		else:
			argv.extend(command)
		p = subprocess.Popen(argv,
			stdout=subprocess.PIPE, stdin=subprocess.DEVNULL, stderr=subprocess.PIPE)
		data = b""
		while True:
			rdata = p.stdout.read()
			if len(rdata) == 0:
				break
			data += rdata
		p.wait()
		return data.split(b"\n", 1)[1]

	def routes(self, table=None, protocol=None, primary=True, all=True, filtered=False):
		command = ["show", "route"]
		if table is not None:
			command.append("table")
			command.append(str(table))
		if all:
			command.append("all")
		if primary:
			command.append("primary")
		if filtered:
			command.append("filtered")
		if protocol is not None:
			command.append(str(protocol))
		res = self.send(command)

		return parse_routes(res.decode().splitlines())
	
	def protocols(self):
		command = ["show", "protocols"]
		res = self.send(command)
		for line in res.splitlines()[1:]:
			t = line.decode().split()
			while len(t) < 7:
				t.append(None)
			yield tuple(t)

def parse_routes(lines):
	lines_iter = iter(lines)

	cur_prefix = None
	cur_route = None
	
	for line in lines_iter:
		if line[0] == "\t":
			# route annotation
			key, value = line.split(":", 1)
			cur_route[key.strip()] = value.strip()
			continue

		if cur_route is not None:
			yield cur_route

		if line[0] != " ":
			cur_prefix, *args = line.split()
		else:
			args = line.split()

		cur_route = lglass.route.Route(cur_prefix)

		if args[0] == "via":
			cur_route.nexthop = (netaddr.IPAddress(args[1]), args[3])

		if args[-2][0] == "(" and args[-2][-1] == ")":
			metric = args[-2][1:-1]
			if "/" in metric:
				metric = metric.split("/", 1)[0]
			cur_route.metric = int(metric)

	if cur_route is not None:
		yield cur_route

