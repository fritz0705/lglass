import datetime

import lglass.database


class CacheProxyDatabase(lglass.database.ProxyDatabase):
    def __init__(self, backend, cache_presence=True, cache_objects=True,
                 lifetime=None, cache_backend=dict):
        super().__init__(backend)
        self.cache_presence = cache_presence
        self.cache_objects = cache_objects
        if isinstance(lifetime, int):
            self.lifetime = datetime.timedelta(lifetime)
        elif isinstance(lifetime, datetime.timedelta):
            self.lifetime = datetime.timedelta(lifetime)
        else:
            self.lifetime = None
        self._cache = cache_backend()

    def fetch(self, object_class, object_key):
        object_class = self.primary_class(object_class)
        if (object_class, object_key) in self._cache:
            obj, expires_at = self._cache[(object_class, object_key)]
            if expires_at is None or expires_at > datetime.datetime.now():
                if obj is False and self.cache_presence:
                    raise KeyError(repr((object_class, object_key)))
                elif self.cache_objects and obj is not True:
                    return obj.copy()
            else:
                del self._cache[(object_class, object_key)]
        expires_at = None
        if self.lifetime is not None:
            expires_at = datetime.datetime.now() + self.lifetime
        try:
            obj = super().fetch(object_class, object_key)
        except KeyError:
            if self.cache_presence:
                self._cache[(object_class, object_key)] = (False, expires_at)
            raise
        if self.cache_objects:
            self._cache[(object_class, object_key)] = (obj, expires_at)
        elif self.cache_presence:
            self._cache[(object_class, object_key)] = (True, expires_at)
        return obj

    def lookup(self, classes=None, keys=None):
        if isinstance(classes, str):
            classes = {classes}
        if isinstance(keys, str):
            keys = {keys}
        for object_class, object_key in super().lookup(classes=classes, keys=keys):
            if (object_class, object_key) not in self._cache and self.cache_presence:
                expires_at = None
                if self.lifetime is not None:
                    expires_at = datetime.datetime.now() + self.lifetime
                self._cache[(object_class, object_key)] = (True, expires_at)
            yield (object_class, object_key)

    def save(self, obj, **options):
        return super().save(obj, **options)

    def clean_cache(self):
        for key, (obj, expires_at) in self._cache.items():
            if expires_at is not None and expires_at <= datetime.datetime.now():
                del self._cache[key]

    def cache_items(self):
        return self._cache.items()

    def update(self, other):
        for key, (obj, expires_at) in other.cache_items():
            self._cache[key] = (obj, expires_at)


class NotifyProxyDatabase(lglass.database.ProxyDatabase):
    def __init__(self, backend, on_update=None, on_delete=None):
        super().__init__(backend)
        self._on_update = on_update
        self._on_delete = on_delete

    def on_update(self, obj):
        if self._on_update is not None:
            self._on_update(obj)

    def on_delete(self, obj):
        if self._on_delete is not None:
            self._on_delete(obj)

    def save(self, obj, **options):
        super().save(obj, **options)
        self.on_update(obj)
