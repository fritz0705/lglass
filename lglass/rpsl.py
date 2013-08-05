# coding: utf-8

# TODO Implement real object parser and attribute parsers

class Object(object):
	""" This object type is some kind of magic: It acts as a dictionary and a
	list, therefore an implementation using a trie would be the best idea.
	Unfortunately, lists are fast enough for our purpose, so we perform linear
	searches. If you have time, implement is as tree. And don't implement it as
	dict. """

	def __init__(self, data=None):
		""" Initialize empty RPSL object and fill it with data by passing its value
		to extend """
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
			for off, kvpair in enumerate(ex):
				if not isinstance(kvpair, tuple):
					raise ValueError("offset {}: expected entry to be tuple, got {}".format(off, type(kvpair)))
				if len(kvpair) != 2:
					raise ValueError("offset {}: expected tuple to have two values, got {}".format(off, len(kvpair)))
				if not isinstance(kvpair[0], str):
					raise ValueError("offset {}: expected key to be str, got {}".format(off, type(kvpair[0])))
				if not isinstance(kvpair[1], str):
					raise ValueError("offset {}: expected value to be str, got {}".format(off, type(kvpair[0])))

			self.data.extend(ex)
		elif isinstance(ex, dict):
			# the same for dicts, we will check the given dict and then we will
			# add the values to the structure
			for key, value in ex.items():
				if not isinstance(key, str):
					raise ValueError("expected key to be str, got {}: {}".format(type(key), key))
				if not isinstance(value, str) and not isinstance(value, list):
					raise ValueError("key {}: expected value to be str or list, got {}".format(key, type(value)))

			for key, value in ex.items():
				if isinstance(value, list):
					for sval in value:
						self.append(key, sval)
				else:
					self[key] = value
		elif isinstance(ex, Object):
			self.data.extend(ex.data)
		else:
			raise TypeError("Expected ex to be dict or list, got {}".format(type(ex)))

	def __getitem__(self, key):
		if isinstance(key, str):
			try:
				return self.get(key)[0][1]
			except IndexError:
				raise KeyError(repr(key))
		elif isinstance(key, int) or isinstance(key, slice):
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
		elif isinstance(key, int):
			if not isinstance(value, tuple):
				raise TypeError("Expected value to be tuple, got {}".format(type(key)))
			self.data[key] = value
		elif isinstance(key, slice):
			if not isinstance(value, list):
				raise TypeError("Expected value to be list, got {}".format(type(key)))
		else:
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
		for offset, kvpair in enumerate(self.data):
			if kvpair[0] == key:
				return offset
		raise ValueError("{} not found".format(key))

	def keys(self):
		""" Return list of all keys. """
		return list(set([kvpair[0] for kvpair in self.data]))

	def pretty_print(self, kv_padding=8):
		try:
			left_padding = sorted([len(k) for k in self.keys()], reverse=True)[0] + kv_padding
		except IndexError:
			return ""
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

	def to_dict(self):
		new_dict = dict()
		for key, value in self:
			if key not in new_dict:
				new_dict[key] = []
			new_dict[key].append(value)
		return new_dict

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
	def from_string(cls, string, *args, **kwargs):
		return cls(parse_rpsl(string.splitlines(), *args, **kwargs))

	@classmethod
	def from_iterable(cls, *args, **kwargs):
		return cls(parse_rpsl(*args, **kwargs))

def parse_rpsl(lines, pragmas={}):
	''' This is a simple RPSL parser which expects an iterable which yields lines.
	This parser processes the object format, not the policy format. The object
	format used by this parser is similar to the format described by the RFC:
	Each line consists of key and value, which are separated by a double-colon ':'.
	The ':' can be surrounded by whitespace characters including line breaks,
	because this parser doesn't split the input into lines; it's newline unaware.
	The format also supports line continuations by beginning a new line of input
	with a whitespace character. This whitespace character is stripped, but the
	parser will produce a '\n' in the resulting value. Line continuations are
	only possible for the value part, which means, that the key and ':' must be
	on the same line of input.

	We also support an extended format using pragmas, which can define the
	processing rules like line-break type, and whitespace preservation. Pragmas
	are on their own line, which must begin with "%!", followed by any
	amount of whitespace, "pragma", at least one whitespace, followed by the
	pragma-specific part.
	
	The following pragmas are supported:

		%! pragma whitespace-preserve [on|off]
				Preserve any whitespace of input in keys and values and don't strip
				whitespace.

		%! pragma newline-type [cr|lf|crlf|none]
				Define type of newline by choosing between cr "Mac OS 9", lf "Unix",
				crlf "Windows" and none.

		%! pragma rfc
				Reset all pragmas to the RFC-conform values.

		%! pragma stop-at-empty-line [on|off]
				Enforces the parser to stop at an empty line

		%! pragma condense-whitespace [on|off]
				Remove any sequence of whitespace characters with Space (' ')
	'''
	result = []
	default_pragmas = {
		"whitespace-preserve": False,
		"newline-type": "lf",
		"stop-at-empty-line": False,
		"condense-whitespace": False
	}
	_pragmas = dict(default_pragmas)
	_pragmas.update(pragmas)
	pragmas = _pragmas

	for line in lines:
		if line.startswith("%!"):
			# this line defines a parser instruction, which should be a pragma
			values = line[2:].strip().split()
			if len(values) <= 1:
				raise ValueError("Syntax error: Expected pragma type after 'pragma'")
			if values[0] != "pragma":
				raise ValueError("Syntax error: Only pragmas are allowed as parser instructions")
			if values[1] == "rfc":
				pragmas.update(default_pragmas)
			elif values[1] == "whitespace-preserve":
				try:
					if values[2] not in ["on", "off"]:
						raise ValueError("Syntax error: Expected 'on' or 'off' as value for 'whitespace-preserve' pragma")
					pragmas["whitespace-preserve"] = True if values[2] == "on" else False
				except IndexError:
					raise ValueError("Syntax error: Expected value after 'whitespace-preserve'")
			elif values[1] == "newline-type":
				try:
					if values[2] not in ["cr", "lf", "crlf", "none"]:
						raise ValueError("Syntax error: Expected 'cr', 'lf', 'crlf' or 'none' as value for 'newline-type' pragma")
					pragmas["newline-type"] = values[2]
				except IndexError:
					raise ValueError("Syntax error: Expected value after 'newline-type'")
			elif values[1] == "stop-at-empty-line":
				try:
					if values[2] not in ["on", "off"]:
						raise ValueError("Syntax error: Expected 'on' or 'off' as value for 'stop-at-empty-line' pragma")
					pragmas["stop-at-empty-line"] = True if values[2] == "on" else False
				except IndexError:
					raise ValueError("Syntax error: Expected value after 'stop-at-empty-line'")
			elif values[1] == "condense-whitespace":
				try:
					if values[2] not in ["on", "off"]:
						raise ValueError("Syntax error: Expected 'on' or 'off' as value for 'condense-whitespace' pragma")
					pragmas["condense-whitespace"] = True if values[2] == "on" else False
				except IndexError:
					raise ValueError("Syntax error: Expected value after 'condense-whitespace'")
			else:
				raise ValueError("Syntax error: Unknown pragma: {}".format(values))
			continue

		# remove any comments (text after % and #)
		line = line.split("%")[0]
		line = line.split("#")[0]

		# continue if line is empty
		if not line.strip():
			if pragmas["stop-at-empty-line"] and len(result) != 0:
				break
			continue

		# check for line continuations
		if line[0] == ' ':
			if not pragmas["whitespace-preserve"]:
				line = line.strip()
			entry = result.pop()
			value = ({
				"cr": "\r",
				"lf": "\n",
				"crlf": "\r\n",
				"none": ""
			}[pragmas["newline-type"]]).join([entry[1], line])
			result.append((entry[0], value))
			continue

		try:
			key, value = line.split(":", 1)
		except ValueError:
			raise ValueError("Syntax error: Missing value")

		if not pragmas["whitespace-preserve"]:
			key = key.strip()
			value = value.strip()

		if pragmas["condense-whitespace"]:
			import re
			value = re.sub(r"[\s]+", " ", value, flags=re.M|re.S)

		result.append((key, value))

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
			return [netaddr.IPNetwork(inetnum.primary_key)]
		except (netaddr.core.AddrFormatError, ValueError):
			if "-" in inetnum.primary_key:
				return inetnum_range(inetnum).cidrs()
			else:
				raise
except LoadError:
	pass

if __name__ == '__main__':
	import argparse
	import sys
	import traceback
	import warnings
	
	argparser = argparse.ArgumentParser(description="Simple tool for RPSL formatting")
	argparser.add_argument("--padding", "-p", default=8, type=int,
			help="Define whitespace padding between key and value")
	argparser.add_argument("--inplace", "-i", nargs="+",
			help="Change the RPSL files in-place")
	argparser.add_argument("--whitespace-preserve", action="store_true", default=False,
			help="Turn the whitespace-preserve pragma on")
	argparser.add_argument("--stop-at-empty-line", action="store_true", default=False,
			help="Turn the stop-at-empty-line pragma on")
	argparser.add_argument("--condense-whitespace", action="store_true", default=False,
			help="Turn the condense-whitespace pragma on")

	args = argparser.parse_args()

	pragmas = {
		"whitespace-preserve": args.whitespace_preserve,
		"stop-at-empty-line": args.stop_at_empty_line,
		"condense-whitespace": args.condense_whitespace
	}

	if args.inplace:
		for file in args.inplace:
			with open(file, "r+") as fh:
				try:
					obj = Object.from_iterable(fh, pragmas=pragmas)
				except:
					warnings.warn("Format of {} is invalid".format(file))
					continue
				fh.seek(0)
				fh.write(obj.pretty_print(kv_padding=args.padding))
				fh.truncate()
	else:
		obj = Object.from_iterable(sys.stdin, pragmas=pragmas)
		sys.stdout.write(obj.pretty_print(kv_padding=args.padding))

