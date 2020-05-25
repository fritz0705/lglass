from abc import ABC, abstractmethod

import lglass.object

object_classes = {}
class_synonyms = []
primary_key_rules = {}


def primary_class(object_class, class_synonyms=class_synonyms,
                  object_classes=object_classes):
    """Find primary class name, i.e. the class synonym which is an object
    class."""
    if isinstance(object_class, lglass.object.Object):
        object_class = object_class.object_class
    for synonym_group in class_synonyms:
        if object_class in synonym_group:
            for synonym in synonym_group:
                if synonym in object_classes:
                    return synonym
    return object_class


def primary_key(obj, primary_key_rules=primary_key_rules,
                primary_class=primary_class):
    """Find primary key by applying primary key rules, determined by the object
    itself or the primary_key_rules dictionary. Depends on the primary class of
    the object."""
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


class Database(ABC):
    """Base class for data sources of lglass.object.Object instances."""
    object_classes = {}
    class_synonyms = []
    primary_key_rules = {}

    @abstractmethod
    def lookup(self, classes=None, keys=None):
        """Lookup object specifications (tuples of primary classes and primary
        keys) in database."""
        ...

    @abstractmethod
    def fetch(self, typ, key):
        """Fetch object by object specification. Raises KeyError when the
        appropriate object is not present."""
        ...

    def try_fetch(self, typ, key):
        """Same as fetch, but returns None instead of raising a KeyError."""
        try:
            return self.fetch(typ, key)
        except KeyError:
            return None

    @abstractmethod
    def save(self, obj, **options):
        """Save object in database."""
        ...

    @abstractmethod
    def delete(self, obj):
        """Delete object in database."""
        ...

    def search(self, query={}, classes=None, keys=None):
        """Perform a complex search in the database, returning objects."""
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
        return self.search({key: set(inverse_values) for key in inverse_keys},
                           classes=classes)

    def find(self, filter=None, classes=None, keys=None):
        """Perform a lookup similarly to lookup, but fetches the objects and
        applies a (optional) filter on the resulting generator."""
        for object_class, object_key in self.lookup(classes=classes, keys=keys):
            try:
                obj = self.fetch(object_class, object_key)
            except:
                continue
            if not filter or filter(obj):
                yield obj

    def primary_class(self, object_class):
        """Return the primary class for an object class, using the database
        internal class synonyms and object classes."""
        return primary_class(object_class, class_synonyms=self.class_synonyms,
                             object_classes=self.object_classes)

    def primary_key(self, object_class):
        """Return the primary key function for an object class."""
        return primary_key(object_class,
                           primary_key_rules=self.primary_key_rules,
                           primary_class=self.primary_class)

    def primary_spec(self, obj):
        """Generate the database-specific primary specification of an
        object."""
        return self.primary_class(obj), self.primary_key(obj)

    @abstractmethod
    def __contains__(self, obj):
        ...

    @abstractmethod
    def close(self):
        ...


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
    """Proxy database, which passes (most) requests to the underlying backend
    database."""

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

    def __contains__(self, obj):
        return obj in self.backend

    def close(self):
        return self.backend.close()

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
