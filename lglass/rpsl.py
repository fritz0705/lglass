# coding: utf-8

class Object(object):
	""" This object type is some kind of magic: It acts as a dictionary and a
	list, therefore an implementation using a trie would be the best idea.
	Unfortunately, lists are fast enough for our purpose, so we perform linear
	searches. If you have time, implement is as tree. And don't implement it as
	dict. """

	_real_primary_key = None
	_real_type = None

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
				if isinstance(kvpair, tuple) or isinstance(kvpair, list):
					if len(kvpair) != 2:
						raise ValueError("offset {}: expected tuple to have two values, got {}".format(off, len(kvpair)))
					elif not isinstance(kvpair[0], str):
						raise ValueError("offset {}: expected key to be str, got {}".format(off, type(kvpair[0])))
					elif not isinstance(kvpair[1], str):
						raise ValueError("offset {}: expected value to be str, got {}".format(off, type(kvpair[0])))

					if kvpair[0] == ":json-real-type":
						self.real_type = kvpair[1]
					elif kvpair[0] == ":json-real-primary-key":
						self.real_primary_key = kvpair[1]
					else:
						self.data.append((kvpair[0], kvpair[1]))
				else:
					raise TypeError("offset {}: expected entry to be tuple, got {}".format(off, type(kvpair)))
		elif isinstance(ex, dict):
			# the same for dicts, we will check the given dict and then we will
			# add the values to the structure
			for key, value in ex.items():
				if not isinstance(key, str):
					raise TypeError("expected key to be str, got {}: {}".format(type(key), key))
				if not isinstance(value, str) and not isinstance(value, list):
					raise TypeError("key {}: expected value to be str or list, got {}".format(key, type(value)))

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
		return "{0}({1!r})".format(self.__class__.__name__, self.data)

	def get(self, key):
		return [kvpair for kvpair in self.data if kvpair[0] == key]

	def add(self, k, v):
		return self.data.append((k, v))

	def remove(self, k):
		self.data = [kvpair for kvpair in self.data if kvpair[0] != k]

	def index(self, key):
		""" Return index of first entry for key. """
		for offset, kvpair in enumerate(self.data):
			if kvpair[0] == key:
				return offset
		raise ValueError("{} not found".format(key))

	def keys(self):
		""" Return iterator which yields all keys. """
		seen = set()
		for key, _ in self.data:
			if key not in seen:
				yield key
				seen.add(key)

	def items(self):
		""" Return iterator which yields all items """
		return iter(self.data)

	def values(self):
		""" Return iterator which yields all values """
		return (kvpair[1] for kvpair in self.data)

	def pretty_print(self, kv_padding=8):
		if len(self) == 0:
			return ""

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

	def __eq__(self, other):
		if hash(self) != hash(other):
			return False
		try:
			return self.data == other.data
		except AttributeError:
			return False
	
	def __ne__(self, other):
		return not self == other

	def __bool__(self):
		return bool(self.data)

	def to_dict(self):
		new_dict = dict()
		for key, value in self:
			if key not in new_dict:
				new_dict[key] = []
			new_dict[key].append(value)
		return new_dict

	def to_json_form(self):
		items = []
		for item in self.items():
			items.append([item[0], item[1]])
		if self._real_type is not None:
			items.append((":json-real-type", self.real_type))
		if self._real_primary_key is not None:
			items.append((":json-real-primary-key", self.real_primary_key))
		return items

	@property
	def type(self):
		try:
			return self.data[0][0]
		except IndexError:
			return None

	@type.setter
	def type(self, new_value):
		if not isinstance(new_value, str):
			raise TypeError("Expected new value for 'type' to be a str, got {}".format(type(new_value)))
		try:
			self.data[0] = (new_value, self.data[0][1])
		except IndexError:
			self.add((new_value, None))

	@property
	def primary_key(self):
		try:
			return self.data[0][1]
		except IndexError:
			return None

	@primary_key.setter
	def primary_key(self, new_value):
		if not isinstance(new_value, str):
			raise TypeError("Expected new value for 'primary_key' to be a str, got {}".format(type(new_value)))
		try:
			self.data[0] = (self.data[0][0], new_value)
		except IndexError:
			self.add((None, new_value))

	@property
	def spec(self):
		""" The spec of an object is a tuple consisting of the type and primary_key. """
		return (self.type, self.primary_key)

	@spec.setter
	def spec(self, new_value):
		if not isinstance(new_value, tuple):
			raise TypeError("Expected tuple as new value for 'spec', got {}".format(type(new_value)))
		elif len(new_value) != 2:
			raise ValueError("Expected new value for 'spec' to have two values, got {}".format(type(new_value)))
		elif not isinstance(new_value[0], str) or not isinstance(new_value[1], str):
			raise ValueError("Expected new value for 'spec' to have two strings as value, got {}".format(new_value))
		try:
			self.data[0] = tuple(new_value)
		except IndexError:
			self.add(*new_value)

	@classmethod
	def from_string(cls, string, *args, **kwargs):
		return cls(parse_rpsl(string.splitlines(), *args, **kwargs))

	@classmethod
	def from_iterable(cls, *args, **kwargs):
		return cls(parse_rpsl(*args, **kwargs))

	@property
	def real_type(self):
		""" The real type is a database-dependent type which addresses the object
		type in the database, due to inconsistence. """
		return self._real_type if self._real_type else self.type

	@real_type.setter
	def real_type(self, new_value):
		self._real_type = new_value

	@property
	def real_primary_key(self):
		""" The real primary key is a database-dependent primary key which was used
		to lookup the object in the database. This is useful in broken databases,
		which don't use the primary_key as file name. """
		return self._real_primary_key if self._real_primary_key else self.primary_key

	@real_primary_key.setter
	def real_primary_key(self, new_value):
		self._real_primary_key = new_value

	@property
	def real_spec(self):
		""" The real_spec is the spec which can be used on databases, if they are
		broken and use a real_primary_key. """
		return (self.real_type, self.real_primary_key)

class SchemaValidationError(Exception):
	def __init__(self, key, message):
		Exception.__init__(self, key, message)
	
	@property
	def key(self):
		return self.args[0]

	@property
	def message(self):
		return self.args[1]

class SchemaObject(Object):
	SCHEMA_SCHEMA = None

	def __init__(self, ex=None):
		Object.__init__(self, ex)
		if ex is not None and self.SCHEMA_SCHEMA is not None:
			self.validate_self()

	def validate_self(self):
		return self.SCHEMA_SCHEMA.validate(self)

	def validate(self, obj):
		validator = SchemaValidator(self)
		return validator.validate(obj)

	def find_inverse(self, db, key, value):
		constraint = self.constraint_for(key)
		if constraint is None or constraint.inverse is None:
			return
		for inverse in constraint.inverse:
			try:
				db.get(inverse, value)
			except KeyError:
				pass
			else:
				yield inverse

	@property
	def type_name(self):
		return self["type-name"][0]

	def constraint_for(self, key):
		for constraint in self.constraints():
			if constraint.key_name == key:
				return constraint
		return None

	def constraints(self):
		for _, value in self.get("key"):
			yield SchemaKeyConstraint.from_string(value)

SchemaObject.SCHEMA_SCHEMA = SchemaObject([
	("schema", "SCHEMA-SCHEMA"),
	("type-name", "schema"),
	("key", "schema mandatory single primary lookup"),
	("key", "type-name mandatory single lookup"),
	("key", "key mandatory multiple")
])

class RIPESchemaObject(SchemaObject):
	def __init__(self, ex=None):
		Object.__init__(self, ex)

	@property
	def type_name(self):
		return self[0][0]

	@property
	def type(self):
		return "schema"

	@property
	def primary_key(self):
		return self.type_name

	def _guess_inverse(self, key):
		lookup = {
			"abuse-mailbox": ["person"],
			"admin-c": ["person"],
			"auth": ["key-cert"],
			"author": ["person"],
			"form": ["poetic-form"],
			"local-as": ["aut-num"],
			"mbrs-by-ref": ["mntner", "route", "inet-rtr"],
			"member-of": ["as-set", "rtr-set", "route-set"],
			"mnt-by": ["mntner"],
			"mnt-domains": ["mntner"],
			"mnt-irt": ["mntner"],
			"mnt-lower": ["mntner"],
			"mnt-nfy": ["person"],
			"mnt-routes": ["mntner"],
			"notify": ["person"],
			"org": ["organisation"],
			"origin": ["aut-num"],
			"ref-nfy": ["person"],
			"tech-c": ["person"],
			"upd-to": ["person"],
			"zone-c": ["person"],
		}
		return lookup[key]
	
	def to_schema(self):
		schema = SchemaObject()
		schema.add("schema", self.primary_key.upper() + "-SCHEMA")
		schema.add("type-name", self.primary_key)
		for constraint in self.constraints():
			keywords = [constraint.key_name]
			keywords.append("multiple" if constraint.multiple else "single")
			keywords.append("mandatory" if constraint.mandatory else "optional")
			if constraint.primary:
				keywords.append("primary")
			if constraint.lookup:
				keywords.append("lookup")
			if constraint.hidden:
				keywords.append("hidden")
			if constraint.inverse:
				keywords.append("inverse")
				keywords.append(",".join(constraint.inverse))
			schema.add("key", " ".join(keywords))
		return schema

	def constraints(self):
		import re

		for key, value in self.data:
			match = re.match(r"\[([^\]]*)\][\s]+\[([^\]]*)\][\s]+\[([^\]]*)\]", value)
			constraint = SchemaKeyConstraint(key)

			if match.group(1) == "mandatory":
				constraint.mandatory = True
			elif match.group(1) == "optional":
				constraint.mandatory = False
			if match.group(2) == "multiple":
				constraint.multiple = True
			elif match.group(2) == "single":
				constraint.multiple = False

			key_constrs = match.group(3).replace("key", "").strip().split("/")
			for key_constr in key_constrs:
				if key_constr == "inverse":
					constraint.inverse = self._guess_inverse(key)
				elif key_constr == "primary":
					constraint.primary = True
				elif key_constr == "lookup":
					constraint.lookup = True
				elif key_constr == "hidden":
					constraint.hidden = True
			
			yield constraint

class SchemaKeyConstraint(object):
	multiple = True
	mandatory = False
	lookup = False
	inverse = None
	primary = False
	hidden = False

	def __init__(self, key_name, **kwargs):
		self.key_name = key_name
		self.__dict__.update(kwargs)

	def validate(self, obj):
		kvpairs = obj.get(self.key_name)
		if self.multiple == False and len(kvpairs) > 1:
			raise SchemaValidationError(self.key_name, "Too much occurrences")
		if self.mandatory == True and len(kvpairs) == 0:
			raise SchemaValidationError(self.key_name, "Key is mandatory but doesn't occur")
		return True

	def __repr__(self):
		keywords = [
			"multiple" if self.multiple else "single",
			"mandatory" if self.mandatory else "optional"
		]
		if self.hidden:
			keywords.append("hidden")
		if self.inverse:
			keywords.append("inverse({0})".format(",".join(self.inverse)))
		if self.primary:
			keywords.append("primary")
		if self.lookup:
			keywords.append("lookup")
		return "SchemaKeyConstraint({1}, {0})".format(" ".join(keywords), self.key_name)

	@classmethod
	def from_string(cls, value):
		key_name, *tokens = value.split()
		tokens_iter = iter(tokens)

		obj = cls(key_name)

		for token in tokens_iter:
			if token == "single":
				obj.multiple = False
			elif token == "multiple":
				obj.multiple = True
			elif token == "mandatory":
				obj.mandatory = True
			elif token == "optional":
				obj.mandatory = False
			elif token == "lookup":
				obj.lookup = True
			elif token == "inverse":
				obj.inverse = next(tokens_iter).split(",")
			elif token == "primary":
				obj.primary = True
			elif token == "hidden":
				obj.hidden = True
			elif token == "visible":
				obj.hidden = False
		return obj

class SchemaValidator(object):
	def __init__(self, schema):
		if not isinstance(schema, Object):
			schema = SchemaObject(schema)
		if not isinstance(schema, SchemaObject):
			schema = SchemaObject(schema)
		self.schema = schema

	def is_valid(self, obj):
		try:
			self.validate(obj)
		except SchemaValidationError:
			return False
		return True

	def validate(self, obj):
		for constraint in self.schema.constraints():
			constraint.validate(obj)
		return True

def parse_rpsl(lines, pragmas={}):
	''' This is a simple RPSL parser which expects an iterable which yields lines.
	This parser processes the object format, not the policy format. The object
	format used by this parser is similar to the format described by the RFC:
	Each line consists of key and value, which are separated by a colon ':'.
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
				Replace any sequence of whitespace characters with simple space (' ')

		%! pragma strict-ripe [on|off]
				Do completely RIPE database compilant parsing, e.g. don't allow any
				space between key and the colon.

		%! pragma hash-comment [on|off]
				Recognize hash '#' as beginning of comment
	'''
	result = []
	default_pragmas = {
		"whitespace-preserve": False,
		"newline-type": "lf",
		"stop-at-empty-line": False,
		"condense-whitespace": False,
		"strict-ripe": False,
		"hash-comment": False
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
			elif values[1] in {"whitespace-preserve", "stop-at-empty-line",
				"condense-whitespace", "strict-ripe", "hash-comment"}:
				try:
					if values[2] not in {"on", "off"}:
						raise ValueError("Syntax error: Expected 'on' or 'off' as value for '{}' pragma".format(values[1]))
					pragmas[values[1]] = True if values[2] == "on" else False
				except IndexError:
					raise ValueError("Syntax error: Expected value after '{}'".format(values[1]))
			elif values[1] == "newline-type":
				try:
					if values[2] not in ["cr", "lf", "crlf", "none"]:
						raise ValueError("Syntax error: Expected 'cr', 'lf', 'crlf' or 'none' as value for 'newline-type' pragma")
					pragmas["newline-type"] = values[2]
				except IndexError:
					raise ValueError("Syntax error: Expected value after 'newline-type'")
			else:
				raise ValueError("Syntax error: Unknown pragma: {}".format(values))
			continue

		# remove any comments (text after % and #)
		line = line.split("%")[0]
		if pragmas["hash-comment"]:
			line = line.split("#")[0]

		# continue if line is empty
		if not line.strip():
			if pragmas["stop-at-empty-line"] and len(result) != 0:
				break
			continue

		# check for line continuations
		if line[0] in [' ', '\t', "+"]:
			line = line[1:]
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

		if pragmas["strict-ripe"]:
			if not re.match("^[a-zA-Z0-9-]+$", key):
				raise ValueError("Syntax error: Key doesn't match RIPE database requirements")

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
except ImportError:
	pass

def main(argv=None):
	import argparse
	import sys
	import traceback
	import warnings
	import pkg_resources
	import lglass.database.file

	if argv is None:
		argv = sys.argv[1:]
	
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
	argparser.add_argument("--validate", "-V", action="store_true",
			help="Validate RPSL against schema")
	argparser.add_argument("--database", "-D",
			default=pkg_resources.resource_filename("lglass", "."),
			help="Database for schema files")

	args = argparser.parse_args(argv)

	database = lglass.database.file.FileDatabase(args.database)

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
					print("{spec}: Format invalid".format(spec=file), file=sys.stderr)
					continue
				if args.validate:
					try:
						schema = database.schema(obj.type)
						schema.validate(obj)
					except lglass.rpsl.SchemaValidationError as e:
						print("{spec}: Validation failed: Key {key}: {message}".format(
							spec=obj.real_spec, key=e.args[0], message=e.args[1]), file=sys.stderr)
						continue
					except KeyError:
						print("{spec}: Schema not found".format(spec=obj.real_spec), file=sys.stderr)
				fh.seek(0)
				fh.write(obj.pretty_print(kv_padding=args.padding))
				fh.truncate()
	else:
		obj = Object.from_iterable(sys.stdin, pragmas=pragmas)
		if args.validate:
			try:
				schema = database.schema(obj.type)
				schema.validate(obj)
			except lglass.rpsl.SchemaValidationError as e:
				print("{spec}: Validation failed: Key {key}: {message}".format(
					spec=obj.real_spec, key=e.args[0], message=e.args[1]), file=sys.stderr)
			except KeyError:
				print("{spec}: Schema not found".format(spec=obj.real_spec), file=sys.stderr)
		sys.stdout.write(obj.pretty_print(kv_padding=args.padding))

if __name__ == '__main__':
	main()

