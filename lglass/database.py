# coding: utf-8

import lglass.object

object_classes = {}
class_synonyms = []
primary_key_rules = {}


def primary_class(object_class, class_synonyms=class_synonyms,
                  object_classes=object_classes):
    if isinstance(object_class, lglass.object.Object):
        object_class = object_class.object_class
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

    def lookup(self, classes=None, keys=None):
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

    def delete(self, obj):
        pass

    def search(self, query={}, classes=None, keys=None):
        for obj in self.find(classes=classes, keys=keys):
            for key, query_value in query.items():
                values = obj.get(key)
                if isinstance(query_value,
                              set) and query_value.intersection(values):
                    yield obj
                    break
                elif isinstance(query_value, str) and query_value in values:
                    yield obj
                    break

    def search_inverse(self, inverse_keys, inverse_values, classes=None):
        return self.search({key: inverse_values for key in inverse_keys},
                classes=classes)

    def find(self, filter=None, classes=None, keys=None):
        for object_class, object_key in self.lookup(classes=classes, keys=keys):
            try:
                obj = self.fetch(object_class, object_key)
            except:
                continue
            if not filter or filter(obj):
                yield obj

    def primary_class(self, object_class):
        return primary_class(object_class, class_synonyms=self.class_synonyms,
                             object_classes=self.object_classes)

    def primary_key(self, object_class):
        return primary_key(object_class,
                           primary_key_rules=self.primary_key_rules,
                           primary_class=self.primary_class)

    def primary_spec(self, obj):
        return self.primary_class(obj), self.primary_key(obj)

    def __contains__(self, obj):
        pass


def perform_key_match(key_pat, key):
    return (
        key_pat is None) or (
        isinstance(
            key_pat,
            str) and key == key_pat) or (
                isinstance(
                    key_pat,
                    (list,
                     set,
                     tuple,
                     frozenset)) and key in key_pat) or (
        callable(key_pat) and key_pat(key))


class ProxyDatabase(Database):
    def __init__(self, backend):
        self.backend = backend

    def lookup(self, *args, **kwargs):
        return self.backend.lookup(*args, **kwargs)

    def save(self, *args, **kwargs):
        return self.backend.save(*args, **kwargs)

    def fetch(self, *args, **kwargs):
        return self.backend.fetch(*args, **kwargs)

    def search(self, *args, **kwargs):
        return self.backend.search(*args, **kwargs)

    def search_inverse(self, *args, **kwargs):
        return self.backend.search_inverse(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.backend.delete(*args, **kwargs)

    def primary_class(self, *args, **kwargs):
        return self.backend.primary_class(*args, **kwargs)

    def primary_key(self, *args, **kwargs):
        return self.backend.primary_key(*args, **kwargs)

    def save_manifest(self, *args, **kwargs):
        return self.backend.save_manifest(*args, **kwargs)

    @property
    def object_classes(self):
        return self.backend.object_classes

    @property
    def class_synonyms(self):
        return self.backend.class_synonyms

    @property
    def primary_key_rules(self):
        return self.backend.primary_key_rules

    @property
    def manifest(self):
        return self.backend.manifest

    @property
    def database_name(self):
        return self.backend.database_name
