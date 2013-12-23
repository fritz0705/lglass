# coding: utf-8

import os.path
import sys
import argparse

class Interface(object):
	def __init__(self, name):
		self.name = name

	@property
	def basepath(self):
		return os.path.join("/sys/class/net/", self.name)

	def statistic(self, name):
		with open(os.path.join(self.basepath, "statistics", name)) as fh:
			return int(fh.read())

	@property
	def rx_bytes(self):
		return self.statistic("rx_bytes")

	@property
	def tx_bytes(self):
		return self.statistic("tx_bytes")

	@property
	def rx_packets(self):
		return self.statistic("rx_packets")

	@property
	def tx_packets(self):
		return self.statistic("tx_packets")

	@property
	def rx_errors(self):
		return self.statistic("rx_errors")

	@property
	def tx_errors(self):
		return self.statistic("tx_errors")

def main(args=sys.argv[1:]):
	argparser = argparse.ArgumentParser()

	argparser.add_argument("interface")
	argparser.add_argument("statistics", nargs="+")

	args = argparser.parse_args(args)

	interface = Interface(args.interface)
	for stat in args.statistics:
		print(getattr(interface, stat))

if __name__ == "__main__":
	main()

