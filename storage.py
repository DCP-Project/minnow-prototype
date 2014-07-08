import time
import shelve
from contextlib import contextmanager
from fcntl import flock, LOCK_EX, LOCK_UN

import acl, config

@contextmanager
def open_db(name):
    f = shelve.open(name)
    flock(f, LOCK_EX)
    yield
    flock(f, LOCK_UN)
    f.close()

class DCPStoredUser:
    version = 2

    def __init__(self, ts, hash, gecos, groups):
        self.ts = ts
        self.hash = hash
        self.gecos = gecos
        self.groups = groups

        self.acl = acl.UserACL()
        self.config = config.UserConfig()
        self.roster = set()

    @classmethod
    def upgrade(cls, old):
        if old.version == cls.version:
            return

        new = None
        if old.version == 1:
            new = DCPStoredUser(old.ts, old.hash, old.gecos, old.groups)

            # ACL format changes
            for acl in old.acl:
                # Version 1 had no reasons
                new.acl[acl] = (0, 'Internal format upgrade')

            # properties -> config (that format has also changed)
            for property in old.property:
                config, sep, value = property.partition(':')
                if not sep:
                    value = None

                new.config[config] = value

        return new

class DCPStoredGroup:
    version = 2

    def __init__(self, ts):
        self.ts = ts

        self.acl = acl.GroupACL()
        self.config = config.GroupConfig()
        self.topic = None

    @classmethod
    def upgrade(cls, old):
        if oldversion == cls.version:
            return

        elif old.version == 1:
            new = DCPStoredGroup(ts)

            # ACL format changes
            for acl in old.acl:
                # Version 1 had no reasons
                new.acl[acl] = (0, 'Internal format upgrade')

            # properties -> config (that format has also changed)
            for property in old.properties:
                config, sep, value = property.partition(':')
                if not sep:
                    value = None

                new.config[config] = value

            return new


class BaseStorage:
    def __init__(self, filename, cls):
        self.filename = filename
        self.cls = cls

        # Cache
        self.cache = dict()

    def get(self, key):
        if key in self.cache:
            return self.cache[key]

        with open_db(self.filename) as db:
            item = db.get(key, None)

            if item and item.version < self.cls.version:
                db[key] = item = self.cls.upgrade(item)

        self.cache[key] = item

        return item

    def add(self, key, *args, **kwargs):
        # Invalidate the cache
        self.cache.pop(key, None)

        item = self.cls(*args, **kwargs)
        with open_db(self.filename) as db:
            db[key] = item

        self.cache[key] = item

    def modify(self, key, **kwargs):
        item = self.cache.pop(key, None)
        if not item:
            with open_db(self.filename) as db:
                item = db.get(key, None)

        if item is None:
            return

        for k, v in kwargs.items():
            setattr(item, k, v)

        with open_db(self.filename) as db:
            db[key] = item

        self.cache[key] = item

    def delete(self, key):
        self.cache.pop(key, None)

        with open_db(self.filename) as db:
            db.pop(key, None)

    def invalidate(self, key):
        self.cache.pop(key)

    def invalidate_all(self, key):
        self.cache.clear()


class UserStorage(BaseStorage):
    def __init__(self, filename='users.db'):
        super().__init__(filename, DCPStoredUser)

    def add(self, key, *args, **kwargs):
        args = (round(time.time()),) + args
        super().add(key, *args, **kwargs)


class GroupStorage(BaseStorage):
    def __init__(self, filename='groups.db'):
        super().__init__(filename, DCPStoredGroup)

    def add(self, key, *args, **kwargs):
        args = (round(time.time()),) + args
        super().add(key, *args, **kwargs)
