# coding: utf-8

import lglass.object

object_classes = {}
class_synonyms = []
primary_key_rules = {}

def primary_class(object_class, class_synonyms=class_synonyms,
        object_classes=object_classes):
    for synonym_group in class_synonyms:
        if object_class in synonym_group:
            for synonyme in synonym_group:
                if synonyme in object_classes:
                    return synonyme
    return object_class

def primary_key(obj, primary_key_rules=primary_key_rules,
        primary_class=primary_class):
    object_class = primary_class(obj.object_class)
    try:
        rule = primary_key_rules[object_class]
    except KeyError:
        if hasattr(obj, "primary_key"):
            return obj.primary_key
        return object_class.object_key
    if callable(rule):
        return rule(obj)
    def _components():
        for component in rule:
            if primary_class(component) == object_class:
                yield obj.object_key
            else:
                yield obj.getfirst(component, default="")
    return "".join(_components())

class Database(object):
    object_classes = {}
    class_synonyms = []
    primary_key_rules = {}

    def lookup(self, types=None, keys=None):
        pass

    def fetch(self, typ, key):
        pass

    def try_fetch(self, typ, key):
        try:
            return self.fetch(typ, key)
        except KeyError:
            return None

    def save(self, obj, **options):
        pass

    def find(self, filter=None, types=None, keys=None):
        for object_class, object_key in self.lookup(types=types, keys=keys):
            obj = self.fetch(object_class, object_key)
            if not filter or filter(obj):
                yield obj

    def primary_class(self, object_class):
        return primary_class(object_class, class_synonyms=self.class_synonyms,
                object_classes=self.object_classes)

    def primary_key(self, object_class):
        return primary_key(object_class, primary_key_rules=self.primary_key_rules,
                primary_class=self.primary_class)

def perform_key_match(key_pat, key):
    return (key_pat is None) or (isinstance(key_pat, str) and key == key_pat) \
            or (isinstance(key_pat, (list, set, tuple, frozenset)) and key in key_pat) \
            or (callable(key_pat) and key_pat(key))

