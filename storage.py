import time
import shelve

class DCPStoredUser:
    version = 1

    def __init__(self, ts, hash, gecos, groups):
        self.ts = ts
        self.hash = hash
        self.gecos = gecos
        self.groups = groups

        self.acl = set()
        self.property = set()
        self.roster = set()


class DCPStoredGroup:
    version = 1

    def __init__(self, ts):
        self.ts = ts

        self.acl = set()
        self.property = set()
        self.topic = None


class BaseStorage:
    def __init__(self, filename, cls):
        self.filename = filename
        self.cls = cls

    def get(self, key):
        with shelve.open(self.filename) as db:
            item = db.get(key, None)

        return item

    def add(self, key, *args, **kwargs):
        item = self.cls(*args, **kwargs)
        with shelve.open(self.filename) as db:
            db[key] = item

    def modify(self, key, **kwargs):
        with shelve.open(self.filename) as db:
            item = db.get(key, None)

        if item is None:
            return

        for k, v in kwargs.items():
            setattr(item, k, v)

        with shelve.open(self.filename) as db:
            db[key] = item

    def delete(self, key):
        with shelve.open(self.filename) as db:
            db.pop(key, None)


class UserStorage(BaseStorage):
    def __init__(self, filename='users.db'):
        super().__init__(filename, DCPStoredUser)

    def add(self, key, *args, **kwargs):
        args = [round(time.time())].extend(args)
        super().add(key, *args, **kwargs)

class GroupStorage(BaseStorage):
    def __init__(self, filename='groups.db'):
        super().__init__(filename, DCPStoredGroup)

    def add(self, key, *args, **kwargs):
        args = [round(time.time())].extend(args)
        super().add(key, *args, **kwargs)
