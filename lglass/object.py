class Object(object):
    def __init__(self, data=None):
        self._data = []
        if data is not None:
            self.extend(data)

    @property
    def data(self):
        """List of key-value-tuples."""
        return self._data

    @property
    def object_class(self):
        """Object class of this object."""
        return self.data[0][0]

    @object_class.setter
    def object_class(self, new_class):
        """Set object class to new value."""
        self.data[0] = (new_class, self.object_key)

    @property
    def object_key(self):
        """Object key of this object."""
        return self.data[0][1]

    @object_key.setter
    def object_key(self, new_key):
        """Set object key to new value."""
        self.data[0] = (self.object_class, new_key)

    @property
    def type(self):
        """Alias of `object_class`."""
        return self.object_class

    @property
    def key(self):
        """Alias of `object_key`."""
        return self.object_key

    @property
    def primary_key(self):
        """Primary key of this object. This is the concatenation of all
        primary key field values."""
        return "".join(self[k] for k in self.primary_key_fields)

    @property
    def primary_key_fields(self):
        """List of primary key fields."""
        return [self.object_class]

    def primary_key_object(self):
        """Return object which consists only of the primary key fields."""
        return self.__class__(
            [(k, v) for k, v in self.data if k in self.primary_key_fields])

    def extend(self, ex, append_group=False):
        """Extend object with another object or list."""
        if isinstance(ex, str):
            ex = parse_object(ex.splitlines())
        self._data.extend(map(tuple, ex))

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.replace("_", "-")
            try:
                return list(self.get(key))[0]
            except IndexError:
                raise KeyError(repr(key))
        elif isinstance(key, (int, slice)):
            return self.data[key]
        raise TypeError(
            "Expected key to be str or int, got {}".format(
                type(key)))

    def __setitem__(self, key, value):
        if isinstance(value, (list, slice, set)):
            for val in value:
                self.append(key, val)
            return
        if isinstance(key, (int, slice)):
            self.data[key] = value
        elif isinstance(key, str):
            key = key.replace("_", "-")
            if key not in self:
                self.append(key, value)
            else:
                index = self.indices(key)[0]
                self.remove(key)
                self.insert(index, key, value)

    def __delitem__(self, key):
        if isinstance(key, (int, slice)):
            key = key.replace("_", "-")
            del self.data[key]
        else:
            self.remove(key)

    def __contains__(self, key):
        """ Checks whether a given key is contained in the object instance. """
        return key in set(self.keys())

    def __len__(self):
        return len(self.data)

    def get(self, key):
        """Return a list of values for a given key."""
        return [v for k, v in self._data if k == key]

    def getitems(self, key):
        """Returns a list of key-value-tuples for a given key."""
        return [kv for kv in self._data if kv[0] == key]

    def getfirst(self, key, default=None):
        """Returns the first occurence of a field with matching key. Supports
        the `default` keyword."""
        try:
            return self.get(key)[0]
        except IndexError:
            return default

    def add(self, key, value, index=None):
        """Append or insert a new field."""
        value = str(value)
        if index is not None:
            self._data.insert(index, (key, value))
        else:
            self._data.append((key, value))

    def append(self, key, value):
        return self.add(key, value)

    def append_group(self, key, value):
        """Appends a field to the last group of fields of the same key."""
        try:
            idx = self.indices(key)[-1] + 1
            return self.insert(idx, key, value)
        except IndexError:
            return self.append(key, value)

    def insert(self, index, key, value):
        return self.add(key, value, index)

    def indices(self, key):
        """Returns a list of indices of fields with a given key."""
        return [i for i, (k, v) in enumerate(self.data) if k == key]

    def remove(self, key):
        """Remove all occurences of a key or remove a field with a given
        index."""
        if isinstance(key, int):
            del self._data[key]
            return
        self._data = [kvpair for kvpair in self._data if kvpair[0] != key]

    def items(self):
        """Returns an iterator of key-value-tuples."""
        return iter(self.data)

    def keys(self):
        """Returns an iterator of field keys."""
        return (key for key, _ in self.items())

    def values(self):
        """Returns an iterator of field values."""
        return (value for _, value in self.items())

    def pretty_print(self, min_padding=0, add_padding=8):
        """Generates a pretty-printed version of the object serialization."""
        padding = max(max((len(k) for k in self.keys()),
                          default=0), min_padding) + add_padding
        for key, value in self:
            value_lines = value.splitlines() or [""]
            record = "{key}:{pad}{value}\n".format(
                key=key,
                pad=" " * (padding - len(key)),
                value=value_lines[0])
            for line in value_lines[1:]:
                if not line:
                    record += "+\n"
                    continue
                record += "{pad}{value}\n".format(
                    pad=" " * (padding + 1),
                    value=line)
            yield record

    def __str__(self):
        return "".join(self.pretty_print())

    def __repr__(self):
        return "<{module_name}.{class_name} {object_class}: {object_key}>".format(
            module_name=type(self).__module__,
            class_name=type(self).__name__,
            object_class=self.object_class,
            object_key=self.object_key)

    def __eq__(self, other):
        if not isinstance(other, Object):
            return NotImplemented
        return self.data == other.data

    def __ne__(self, other):
        return not self == other

    def __bool__(self):
        return bool(self.data)

    def copy(self):
        """Creates new object with same content."""
        return self.__class__(self.data)

    def to_json(self):
        return list(map(list, self.data))

    @classmethod
    def from_file(cls, fh):
        """Creates an object from a file stream."""
        return cls(fh.read())

    @classmethod
    def from_str(cls, string):
        """Creates an object from a string representation."""
        return cls(string)


def parse_objects(lines, pragmas={}):
    lines_iter = iter(lines)
    obj = []
    for line in lines_iter:
        if not line.strip() and obj:
            obj = parse_object(obj, pragmas=pragmas)
            if obj:
                yield obj
            obj = []
        else:
            obj.append(line)
    if obj:
        obj = parse_object(obj, pragmas=pragmas)
        if obj:
            yield obj

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
                raise ValueError(
                    "Syntax error: Expected pragma type after 'pragma'")
            if values[0] != "pragma":
                raise ValueError(
                    "Syntax error: Only pragmas are allowed as parser instructions")
            if values[1] == "rfc":
                pragmas.update(default_pragmas)
            elif values[1] in {"whitespace-preserve", "stop-at-empty-line",
                               "condense-whitespace", "strict-ripe", "hash-comment"}:
                try:
                    if values[2] not in {"on", "off"}:
                        raise ValueError(
                            "Syntax error: Expected 'on' or 'off' as value for '{}' pragma".format(
                                values[1]))
                    pragmas[values[1]] = True if values[2] == "on" else False
                except IndexError:
                    raise ValueError(
                        "Syntax error: Expected value after '{}'".format(
                            values[1]))
            elif values[1] == "newline-type":
                try:
                    if values[2] not in ["cr", "lf", "crlf", "none"]:
                        raise ValueError(
                            "Syntax error: Expected 'cr', 'lf', 'crlf' or 'none' as value for 'newline-type' pragma")
                    pragmas["newline-type"] = values[2]
                except IndexError:
                    raise ValueError(
                        "Syntax error: Expected value after 'newline-type'")
            else:
                raise ValueError(
                    "Syntax error: Unknown pragma: {}".format(values))
            continue

        # continue if line is empty
        if not line.strip():
            if pragmas["stop-at-empty-line"]:
                break
            continue

        # remove any comments (text after % and #)
        line = line.split("%")[0]
        if pragmas["hash-comment"]:
            line = line.split("#")[0]

        if not line.strip():
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
            import re
            if not re.match("^[a-zA-Z0-9-]+$", key):
                raise ValueError(
                    "Syntax error: Key doesn't match RIPE database requirements")

        if not pragmas["whitespace-preserve"]:
            key = key.strip()
            value = value.strip()

        if pragmas["condense-whitespace"]:
            import re
            value = re.sub(r"[\s]+", " ", value, flags=re.M | re.S)

        result.append((key, value))

    return result


def main():
    import argparse
    import sys

    argparser = argparse.ArgumentParser(description="Pretty-print objects")
    argparser.add_argument(
        "--min-padding",
        help="Minimal padding between key and value",
        type=int,
        default=0)
    argparser.add_argument(
        "--add-padding",
        help="Additional padding between key and value",
        type=int,
        default=8)
    argparser.add_argument("--whois-format", action="store_true")
    argparser.add_argument("--tee", "-T", action="store_true")
    argparser.add_argument("--inplace", "-i", action="store_true")
    argparser.add_argument("files", nargs='*', help="Input files")

    args = argparser.parse_args()

    options = dict(
        min_padding=args.min_padding,
        add_padding=args.add_padding)
    if args.whois_format:
        options["min_padding"] = 16
        options["add_padding"] = 0

    if not args.files:
        obj = Object.from_file(sys.stdin)
        print("".join(obj.pretty_print(**options)))
        return

    for f in args.files:
        with open(f, "r") as fh:
            obj = Object.from_file(fh)
        if args.inplace:
            with open(f, "w") as fh:
                fh.write("".join(obj.pretty_print(**options)))
        if args.tee or not args.inplace:
            print("".join(obj.pretty_print(**options)))


if __name__ == "__main__":
    main()
