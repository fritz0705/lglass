# coding: utf-8

import netaddr
import re

class QueryError(Exception):
	pass

class ResultSet(object):
	def __init__(self, query, exact=[], related=[], inverse=[]):
		self.query = query
		self.exact = exact.copy()
		self.related = related.copy()
		self.inverse = inverse.copy()
	
	@property
	def result(self):
		return self.exact.get(0)

	def __len__(self):
		return len(self.exact)
	
	def __iter__(self):
		for exact in self.exact:
			yield ex
		for related in self.related:
			yield related
		for inverse in self.inverse:
			yield from inverse

class Query(object):
	_query_type = None

	def __init__(self, term, source=None, types=None, inverse_level=1,
			related=True, inverse=True):
		self.term = str(term)
		self.source = source
		if self.source is None and "@" in self.term:
			self.source, self.term = self.term.split("@", 1)
		self.types = set(types) if types is not None else None
		self.inverse_level = inverse_level
		self.related = related
		self.inverse = inverse

	def copy(self):
		return Query(self.term, self.source, self.types, self.inverse_level,
			self.related, self.inverse)

	@property
	def autnum(self):
		if self.query_type != "as-number":
			return None
		return int(self.term[2:])
	
	@property
	def query_type(self):
		if self._query_type is None:
			self._query_type = self._guess_query_type()
		return self._query_type

	@query_type.setter
	def query_type(self, value):
		if value not in {None, "ip-lookup", "as-number", "primary", "lookup"}:
			raise QueryError()
		self._query_type = value
		pass

	def _guess_query_type(self):
		try:
			netaddr.IPNetwork(self.term)
		except netaddr.core.AddrFormatError:
			pass
		else:
			return "ip-lookup"
		if re.match("AS[0-9]+$", self.term):
			# this won't match objects like AS64712:AS-PEERS
			return "as-number"
		return "primary"
		pass

class DefaultCollector(object):
	def __init__(self, source):
		self.sources = {None: source}

	def query(self, *args, **kwargs):
		return self.execute(Query(*args, **kwargs))

	def execute(self, query):
		rs = ResultSet(query)
		try:
			source = self.sources[query.source]
		except KeyError:
			raise QueryError()
		# Get exact results
		rs.exact = list(source.query(query))
		if query.related:
			if query.query_type == "ip-lookup":
				rs.related = list(source.query_ipaddress(query))
			elif query.query_type == "as-number":
				rs.related = list(source.query_autnum(query))
		# TODO implement inverse search
		if query.inverse:
			pass
		return rs

