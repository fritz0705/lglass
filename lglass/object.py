# coding: utf-8

class Object(object):
    def __init__(self, data=None, **kwargs):
        self._data = []
        if data is not None:
            self.extend(data)
        if kwargs != {}:
            self.extend(kwargs)

    @property
    def data(self):
        return self._data

    @property
    def object_class(self):
        return self.data[0][0]

    @object_class.setter
    def object_class(self, new_class):
        self.data[0] = (new_class, self.object_key)

    @property
    def object_key(self):
        return self.data[0][1]

    @object_key.setter
    def object_key(self, new_key):
        self.data[0] = (self.object_class, new_key)

    @property
    def type(self):
        return self.object_class

    @property
    def key(self):
        return self.object_key

    @property
    def primary_key(self):
        return self.object_key

    def extend(self, ex):
        if isinstance(ex, list):
            for offset, item in enumerate(ex):
                if isinstance(item, (tuple, list)):
                    if len(item) != 2:
                        raise ValueError("offset {}: expected tuple of length 2, got {}".format(offset))
                    elif not isinstance(item[0], str):
                        raise ValueError("offset {}: expected key to be of type str, got {}".format(offset, type(item[0])))
                    elif not isinstance(item[1], str):
                        raise ValueError("offset {}: expected value to be of type str, got {}".format(offset, type(item[1])))
                else:
                    raise TypeError("offset {}: expected entry to be of type tuple, got {}".format(offset, item))
            for key, value in ex:
                self.add(key, value)
        elif isinstance(ex, dict):
            for key, value in ex:
                if not isinstance(key, str):
                    raise ValueError("expected key to be of type str, got {}".format(type(key)))
                elif not isinstance(value, (str, list)):
                    raise ValueError("expected value to be of type str or list, got {}".format(type(value)))
                if isinstance(value, list):
                    for off, val in enumerate(value):
                        if not isinstance(val, str):
                            raise ValueError("key {} offset {}: expected value to be of type str, got {}".format(key, off, type(val)))
            for key, value in ex:
                if isinstance(value, list):
                    for val in value:
                        self.add(key, val)
                else:
                    self.add(key, value)
            pass
        elif isinstance(ex, str):
            self.extend(parse_object(ex.splitlines()))
        elif isinstance(ex, Object):
            self.extend(ex.data)
        elif hasattr(ex, "__iter__"):
            self.extend(list(ex))
        else:
            raise TypeError("Expected ex to be dict, list, str, or lglass.object.Object, got {}".format(type(ex)))

    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                return list(self.get(key))[0]
            except IndexError:
                raise KeyError(repr(key))
        elif isinstance(key, (int, slice)):
            return self.data[key]
        raise TypeError("Expected key to be str or int, got {}".format(type(key)))
    
    def __setitem__(self, key, value):
        if isinstance(key, int):
            pass
        elif isinstance(key, str):
            if key not in self:
                self.append(key, value)

    def __delitem__(self, key):
        return self.remove(key)
    
    def __contains__(self, key):
        for key1 in self.keys():
            if key1 == key:
                return True
        return False

    def __len__(self):
        return len(self.data)

    def get(self, key):
        return (v for k, v in self._data if k == key)

    def getfirst(self, key, default=None):
        return next(self.get(key), default)

    def add(self, key, value, index=None):
        if index is not None:
            return self.insert(index, key, value)
        return self.append(key, value)

    def append(self, key, value):
        return self._data.append((key, value))

    def insert(self, index, key, value):
        return self._data.insert(index, (key, value))

    def indices(self, key):
        return [i for i, (k, v) in enumerate(self.data) if k == key]

    def remove(self, key, nth=None):
        if isinstance(key, int):
            del self._data[key]
            return
        self._data = [kvpair for kvpair in self._data if kvpair[0] != key]

    def items(self):
        return iter(self.data)

    def keys(self):
        return (key for key, _ in self.items())

    def values(self):
        return (value for _, value in self.items())

    def pretty_print(self, min_padding=0, add_padding=8):
        padding = max(max((len(k) for k in self.keys()), default=0), min_padding) + add_padding
        for key, value in self:
            value_lines = value.splitlines() or [""]
            record = "{key}:{pad}{value}\n".format(
                    key=key,
                    pad=" " * (padding - len(key)),
                    value=value_lines[0])
            for line in value_lines[1:]:
                record += "{pad}{value}\n".format(
                        pad=" " * (padding + 1),
                        value=line)
            yield record

    def __str__(self):
        return "".join(self.pretty_print())

    def __hash__(self):
        return hash((self.type, self.key))

    def __eq__(self, other):
        if hash(self) != hash(other):
            return false
        try:
            return self.data == other.data
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self == other

    def __bool__(self):
        return bool(self.data)

    @classmethod
    def from_file(cls, fh):
        return cls(fh.read())

# TODO rewrite object parser
def parse_object(lines, pragmas={}):
	r'''This is a simple RPSL parser which expects an iterable which yields lines.
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

		``%! pragma whitespace-preserve [on|off]``
				Preserve any whitespace of input in keys and values and don't strip
				whitespace.

		``%! pragma newline-type [cr|lf|crlf|none]``
				Define type of newline by choosing between cr "Mac OS 9", lf "Unix",
				crlf "Windows" and none.

		``%! pragma rfc``
				Reset all pragmas to the RFC-conform values.

		``%! pragma stop-at-empty-line [on|off]``
				Enforces the parser to stop at an empty line

		``%! pragma condense-whitespace [on|off]``
				Replace any sequence of whitespace characters with simple space (' ')

		``%! pragma strict-ripe [on|off]``
				Do completely RIPE database compilant parsing, e.g. don't allow any
				space between key and the colon.

		``%! pragma hash-comment [on|off]``
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

if __name__ == "__main__":
    import argparse
    import sys

    argparser = argparse.ArgumentParser(description="Pretty-print objects")
    argparser.add_argument("--min-padding", help="Minimal padding between key and value", type=int, default=0)
    argparser.add_argument("--add-padding", help="Additional padding between key and value", type=int, default=8)
    argparser.add_argument("files", nargs='*', help="Input files")

    args = argparser.parse_args()

    options = dict(
            min_padding=args.min_padding,
            add_padding=args.add_padding)

    if not args.files:
        obj = Object.from_file(sys.stdin)
        print("".join(obj.pretty_print(**options)))
    else:
        for f in args.files:
            with open(f) as fh:
                obj = Object.from_file(fh)
                print("".join(obj.pretty_print(**options)))

