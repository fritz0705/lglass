# coding: utf-8

import os
import re

import netaddr

import lglass.object

def range_to_network(rng):
    if isinstance(rng, lglass.object.Object):
        rng = rng.key
    if "-" not in rng:
        return rng
    lower, upper = rng.split("-", 1)
    lower = lower.strip()
    upper = upper.strip()
    return str(netaddr.IPRange(lower, upper).cidrs()[0])

def normalize_as_block(asb):
    if isinstance(asb, lglass.object.Object):
        asb = asb.key
    return "-".join(s.strip() for s in asb.split("-"))

object_types = {"as-block", "as-set", "aut-num", "domain", "inet6num",
        "inetnum", "key-cert", "mntner", "organisation", "person", "role",
        "route", "route6", "route-set"}
type_synonyms = [{"dns", "domain"}]
primary_key_rules = {
        "route": ["route", "origin"],
        "route6": ["route6", "origin"],
        "person": ["nic-hdl"],
        "role": ["nic-hdl"],
        "inetnum": lambda x: str(lglass.object.cidr_key(x)),
        "as-block": normalize_as_block}

def intrinsic_type(typ, type_synonyms=type_synonyms, object_types=object_types):
    for synonym_group in type_synonyms:
        if typ in synonym_group:
            for synonyme in synonym_group:
                if synonyme in object_types:
                    return synonyme
    return typ

def primary_key(obj, primary_key_rules=primary_key_rules, intrinsic_type=intrinsic_type):
    typ = intrinsic_type(obj.type)
    try:
        rule = primary_key_rules[typ]
    except KeyError:
        return obj.key
    if callable(rule):
        return rule(obj)
    def _components():
        for component in rule:
            if intrinsic_type(component) == typ:
                yield obj.key
            else:
                yield obj.getfirst(component, default="")
    return "".join(_components())

class SimpleDatabase(object):
    object_types = object_types
    type_synonyms = type_synonyms
    primary_key_rules = primary_key_rules

    def __init__(self, path):
        self._path = path

    def lookup(self, types=None, keys=None):
        if types is None:
            types = self.object_types
        elif isinstance(types, str):
            types = {self._intrinsic_type(types)}
        else:
            types = map(self._intrinsic_type, types)
        for typ in types:
            try:
                yield from self._lookup_type(typ, keys)
            except FileNotFoundError:
                pass
    
    def find(self, filter=None, types=None, keys=None):
        for typ, key in self.lookup(types=types, keys=keys):
            obj = self.fetch(typ, key)
            if not filter or filter(obj):
                yield obj

    def _lookup_type(self, typ, keys):
        for key in os.listdir(os.path.join(self._path, typ)):
            key = self._mangle_filename(key)
            if perform_key_match(keys, key):
                yield (typ, key)

    def _mangle_filename(self, key):
        return key.replace("_", "/")

    def _mangle_key(self, key):
        return key.replace("/", "_")

    def _object_key(self, obj):
        pass

    def fetch(self, typ, key):
        typ = self._intrinsic_type(typ)
        key = self._mangle_key(key)
        try:
            with open(os.path.join(self._path, typ, key)) as fh:
                return lglass.object.Object.from_file(fh)
        except (FileNotFoundError, IsADirectoryError):
            raise KeyError(repr((typ, key)))
        except ValueError as verr:
            raise ValueError((typ, key), *verr.args)

    def try_fetch(self, typ, key):
        try:
            return self.fetch(typ, key)
        except KeyError:
            pass

    def fetch_spec(self, spec):
        return self.fetch(*spec)

    def save(self, obj, **options):
        typ, key = self._intrinsic_type(obj.type), self._mangle_key(self._primary_key(obj))
        try:
            os.mkdir(os.path.join(self._path, typ))
        except FileExistsError:
            pass
        with open(os.path.join(self._path, typ, key), "w") as fh:
            fh.write("".join(obj.pretty_print(**options)))

    def _intrinsic_type(self, typ):
        return intrinsic_type(typ, type_synonyms=self.type_synonyms,
                object_types=self.object_types)

    def _primary_key(self, typ):
        return primary_key(typ, primary_key_rules=self.primary_key_rules,
                intrinsic_type=self._intrinsic_type)

def whois_lookup(db, term):
    if term.startswith("AS") and "-" in term:
        yield from db.lookup(types="as-block", keys=term)
    elif term.startswith("AS"):
        yield from db.lookup(types="aut-num", keys=term)
    elif term.startswith("ORG-"):
        yield from db.lookup(types="organisation", keys=term)
    elif term.endswith("-MNT"):
        yield from db.lookup(types="mntner", keys=term)
    else:
        yield from db.lookup(keys=term)

def cidr_lookup(db, prefix, allowed_types={"route6", "route", "inet6num", "inetnum"}):
    if not isinstance(prefix, netaddr.IPNetwork):
        prefix = netaddr.IPNetwork(prefix)
    types = {"inet6num", "route6"}
    if prefix.version == 4:
        types = {"inetnum", "route"}
    types = types.intersection(allowed_types)
    keys = set(str(s) for s in prefix.supernet())
    keys.add(str(prefix))
    yield from db.lookup(types=types, keys=keys)

def perform_key_match(key_pat, key):
    return (key_pat is None) or (isinstance(key_pat, str) and key == key_pat) \
            or (isinstance(key_pat, (list, set, tuple, frozenset)) and key in key_pat) \
            or (callable(key_pat) and key_pat(key))

