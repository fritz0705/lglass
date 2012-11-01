# coding: utf-8

import lglass
import lglass.rpsl
import select

class WhoisServer:
	database = None

	def __init__(self, database=None):
		if database is not None:
			self.database = database
		elif self.database is None:
			self.database = lglass.rpsl.MemoryDatabase()

	def on_request(self, request, socket):
		pass

if __name__ == '__main__':
	import argparse
	argparser = argparse.ArgumentParser(description="Simple whois server implementation")
	pass
