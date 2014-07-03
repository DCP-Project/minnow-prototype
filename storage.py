import time
import shelve

class DCPStoredUser:
    def __init__(self, ts, hash, gecos, groups):
        self.ts = ts
        self.hash = hash
        self.gecos = gecos
        self.groups = groups

        # Reserved
        self.acls = set()

class UserStorage:
    def __init__(self, filename='users.db'):
        self.filename = filename

    def get(self, handle):
        with shelve.open(self.filename) as db:
            user = db.get(handle, None)

        return user

    def add(self, handle, hash, gecos, groups):
        user = DCPStoredUser(round(time.time()), hash, gecos, groups)
        with shelve.open(self.filename) as db:
            db[handle] = user

    def modify(self, handle, *, hash=None, gecos=None, groups=None):
        assert all(x for x in (hash, gecos, groups))

        with shelve.open(self.filename) as db:
            user = db.get(handle, None)

        if user is None:
            return

        if hash is not None:
            user.hash = hash

        if gecos is not None:
            user.gecos = gecos

        if groups is not None:
            user.groups = groups
        
        with shelve.open(self.filename) as db:
            del db[handle]
            db[handle] = user

    def delete(self, handle):
        with shelve.open(self.filename) as db:
            del db[handle]
