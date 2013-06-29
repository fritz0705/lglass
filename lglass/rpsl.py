# coding: utf-8

# TODO Implement real object parser and attribute parsers

class Object(object):
	""" This object type is some kind of magic: It acts as a dictionary and a
	list, therefore an implementation using a trie would be the best idea.
	Unfortunately, lists are fast enough for our purpose, so we perform linear
	searches. If you have time, implement is as tree. And don't implement it as
	dict. """

	def __init__(self, data=None):
		self.data = []
		if data:
			self.extend(data)

	def extend(self, ex):
		""" expand has also multiple behaviours depending on given data types. If
		ex is a list of tuples, then this is simply appended as key-value-pairs to
		the structure. Otherwise, if ex is a dict, then __setitem__ will be used on
		the values of struct """

		if isinstance(ex, list):
			# at first we will check the whole struture of ex, if we encounter any
			# error, we will raise an exception, so we are never in undefined state
			for off, kvpair in zip(range(len(ex)), ex):
				if not isinstance(kvpair, tuple):
					raise ValueError("offset {}: expected entry to be tuple, got {}".format(off, type(kvpair)))
				if len(kvpair) != 2:
					raise ValueError("offset {}: expected tuple to have two values, got {}".format(off, len(kvpair)))
				if not isinstance(kvpair[0], str):
					raise ValueError("offset {}: expected key to be str, got {}".format(off, type(kvpair[0])))
				if not isinstance(kvpair[1], str):
					raise ValueError("offset {}: expected value to be str, got {}".format(off, type(kvpair[0])))

			self.data.extend(ex)
			return
		elif isinstance(ex, dict):
			# the same for dicts, we will check the given dict and then we will
			# add the values to the structure
			for key, value in ex.items():
				if not isinstance(key, str):
					raise ValueError("expected key to be str, got {}: {}".format(type(key), key))
				if not isinstance(value, str):
					raise ValueError("key {}: expected value to be str, got {}".format(key, type(value)))

			for key, value in ex.items():
				self[key] = value
			return
		raise TypeError("Expected ex to be dict or list, got {}".format(type(ex)))

	def __getitem__(self, key):
		if isinstance(key, str):
			try:
				return self.get(key)[0][1]
			except IndexError:
				raise KeyError(repr(key))
		elif isinstance(key, int):
			return self.data[key]

		raise TypeError("Expected key to be str or int, got {}".format(type(key)))

	def __len__(self):
		return len(self.data)

	def __contains__(self, key):
		""" __contains__ checks whether a given key of type str is present in the
		structure or not. """
		if isinstance(key, str):
			return len(self.get(key)) > 0

		raise TypeError("Expected key to be str, got {}".format(type(key)))

	def __setitem__(self, key, value):
		""" __setitem__ has special behaviour on this object type: If key is an
		instance of str, then it will remove entry with "key" and append key and
		value to end. In that case, value can be iterable, so multiple new entries
		will be emmitted. Otherwise, if key is a simple number, then it works as
		in lists: It will simply replace the entry with value. In that case, value
		needs to be a tuple of (k, v), where k is the string key and v is the
		string value. """
		if isinstance(key, str):
			if not isinstance(value, list) and not isinstance(value, str):
				raise TypeError("Expected value to be str or list, got {}".format(type(key)))
			del self[key]
			if isinstance(value, list):
				for v in value:
					self.add(key, v)
			else:
				self.add(key, value)
			return
		elif isinstance(key, int):
			if not isinstance(value, tuple):
				raise TypeError("Expected value to be tuple, got {}".format(type(key)))
			self.data[key] = value
			return

		raise TypeError("Expected key to be str or int, got {}".format(type(key)))

	def __delitem__(self, key):
		""" __delitem__ has also special semantics. If key is an instance of str,
		then this will delete any entry with the given key, otherwise if key is an
		instance of int, then this will delete the n'th entry. """
		if isinstance(key, str):
			while key in self.keys():
				del self.data[self.index(key)]
			return

		del self.data[key]

	def __iter__(self):
		return iter(self.data)

	def __repr__(self):
		return repr(self.data)

	def get(self, key):
		return [kvpair for kvpair in self.data if kvpair[0] == key]

	def add(self, k, v):
		return self.data.append((k, v))

	def remove(self, k):
		return self.data.remove(k)

	def index(self, key):
		""" Return index of first entry for key. """
		for kvpair, offset in zip(self.data, range(len(self.data))):
			if kvpair[0] == key:
				return offset
		raise ValueError("{} not found".format(key))

	def keys(self):
		""" Return list of all keys. """
		return list(set([kvpair[0] for kvpair in self.data]))

	def pretty_print(self, kv_padding=8):
		left_padding = sorted([len(k) for k in self.keys()], reverse=True)[0] + kv_padding
		result = []

		for key, value in self:
			result.append(key)
			result.append(":")
			result.append(" " * (left_padding - len(key) - 1))
			value_lines = value.split("\n")
			result.append(value_lines[0])
			for value_line in value_lines[1:]:
				result.append("\n")
				result.append(" " * left_padding)
				result.append(value_line)
			result.append("\n")

		return "".join(result)

	def __str__(self):
		return self.pretty_print()

	def __hash__(self):
		return hash((self.type, self.primary_key))

	@property
	def type(self):
		return self.data[0][0]

	@property
	def primary_key(self):
		return self.data[0][1]

	@property
	def spec(self):
		return (self.type, self.primary_key)

	@classmethod
	def from_string(cls, string):
		return cls(parse_rpsl(string.split("\n")))

def parse_rpsl(lines):
	""" Simple RPSL "parser", which expects a list of lines as input """
	result = []

	for line in lines:
		# remove any comments (text after % and #)
		line = line.split("%")[0]
		line = line.split("#")[0]

		# continue if line is empty
		if not line.strip():
			continue

		# check for line continuations
		if line[0] == ' ':
			entry = result.pop()
			value = "\n".join([entry[1], line.strip()])
			result.append((entry[0], value))
			continue

		key, value = line.split(":", 1)

		result.append((key.strip(), value.strip()))

	return result

try:
	import netaddr

	def inetnum_range(inetnum):

		if isinstance(inetnum, Object):
			inetnum = inetnum.primary_key

		return netaddr.IPRange(*[ipr.strip() for ipr in inetnum.split("-", 1)])

	def inetnum_cidrs(inetnum):
		""" Return all CIDRs included in given inetnum object. """

		try:
			return netaddr.IPNetwork(inetnum.primary_key)
		except (netaddr.core.AddrFormatError, ValueError):
			if "-" in inetnum.primary_key:
				return inetnum_range(inetnum).cidrs()
			else:
				raise
except LoadError:
	pass
