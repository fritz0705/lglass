# coding: utf-8

import marshal

class MemoryCache(object):
	def __init__(self):
		self.invalidate_all()

	def invalidate_all(self):
		self._backend = {}
	
	def cache_query(self, query, result_set):
		self._backend[query] = result_set

	def invalidate_query(self, query):
		del self._backend[query]

	def fetch_query(self, query):
		try:
			return self._backend[query]
		except KeyError:
			pass

