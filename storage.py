import asyncio
import sqlite3
import queue
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from logging import getLogger
from functools import partial


class Counter:
    """ Atomic add/subtract-and-get class """

    __slots__ = ['counter_lock', 'counter']

    def __init__(self):
        self.counter_lock = Lock()
        self.counter = 0

    def inc(self):
        with self.counter_lock:
            self.counter += 1
            return self.counter

    def dec(self):
        with self.counter_lock:
            self.counter -= 1
            return self.counter

    def get(self):
        with self.counter_lock:
            return self.counter


class DatabaseLocks:
    """ The locks for the database - one of these instances per db """

    __slots__ = ['waiting', 'accessing', 'nreaders']

    def __init__(self):
        self.waiting = Lock()
        self.accessing = Lock()
        self.nreaders = Counter()

_db_locks = defaultdict(DatabaseLocks)


class Database:
    """ A class providing readers/writers locks to an SQLite database.
    As many readers as one wants can use the db, but writers only go one at a
    time, and block everything.

    Algorithim based on:
    http://en.wikipedia.org/wiki/Readers%E2%80%93writers_problem - see
    solution #3. Note that we use locks, NOT semaphores.
    """

    def __init__(self, dbname='store.db'):
        # check_same_thread is acceptable because this limitation has not
        # existed since time immemorial.
        self.conn = sqlite3.connect(dbname, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self.locks = _db_locks[dbname]

    def __del__(self):
        self.conn.close()

    def close(self):
        """ Called to close the database. Acquires the waiting locks, commits
        all outstanding transactions, then poof. """
        with self.locks.waiting:
            with self.locks.accessing:
                self.conn.commit()
                self.conn.close()

    def modify(self, *data, func=None):
        """ Call this if your statement even THINKS of writing to the
        database. """
        if func is None:
            func = self.conn.execute
        else:
            func = getattr(self.conn, func)

        with self.locks.waiting:
            self.locks.accessing.acquire()

        try:
            with self.conn:
                return func(*data)
        finally:
            self.locks.accessing.release()

    def read(self, *data, func=None):
        """ Call this if your statement reads from the database """
        if func is None:
            func = self.conn.execute
        else:
            func = getattr(self.conn, func)

        with self.locks.waiting:
            val = self.locks.nreaders.inc()

            if val == 1:
                self.locks.accessing.acquire()

        try:
            return func(*data)
        finally:
            val = self.locks.nreaders.dec()
            if val == 0:
                self.locks.accessing.release()


# Statements
s_get_user = 'SELECT "user".* FROM "user" WHERE "name"=?'

s_get_user_acl = 'SELECT "acl_user".acl,"acl_user".timestamp,"user2".name ' \
    'FROM "acl_user","user" WHERE "user".name=? AND ' \
    '"acl_user".user_id="user".id LEFT OUTER JOIN user AS user2 ' \
    '"acl_user".setter_id="user2".id'

s_get_user_config = 'SELECT "config_user".* FROM "config_user","user" WHERE ' \
    '"user".name=? AND "config_user".user_id="user".id'

s_get_group = 'SELECT "group".* FROM "group" WHERE "name"=?'

s_get_group_acl = 'SELECT "acl_group".acl,"acl_group".timestamp,"user".name ' \
    'FROM "acl_group","group" WHERE "group".name=? LEFT OUTER JOIN "user" ' \
    'ON "acl_group".user_id="user".id'

s_get_group_acl_user = 'SELECT "acl_group".*,"user2".name FROM ' \
    '"acl_group","user" WHERE "group".name=? AND "user".name=? ' \
    'AND "group".id="acl_group".group_id AND "user".id="acl_user".user_id ' \
    'LEFT OUTER JOIN "user" as "user2" "acl_user".setter_id="user2".id'

s_get_group_config = 'SELECT "config_group".*,"user".name AS username FROM ' \
    '"config_group","user","group" WHERE "group".name=? AND ' \
    '"group".id="config_group".group_id AND "user".id="config_group".user_id'

s_create_user = 'INSERT INTO "user" (name,gecos,password) VALUES (?,?,?)'

s_create_group = 'INSERT INTO "group" (name,topic) VALUES(?,?)'

s_create_user_acl = 'INSERT INTO "acl_user" (acl,user_id,reason) VALUES(' \
    '(SELECT ?,"user".id FROM "user" WHERE "user".name=?), ?)'

s_create_group_acl = 'INSERT INTO "acl_group" (acl,group_id,user_id,' \
    'setter_id,reason) VALUES((SELECT ?),(SELECT "group".id FROM "group" ' \
    'WHERE "group".name=?),(SELECT "user".id FROM "user" WHERE ' \
    '"user".name=?), (SELECT "user".id FROM "user" WHERE "user".name=?), ?)'

s_set_user = 'UPDATE "user" SET gecos=IFNULL(?,gecos),password=' \
    'IFNULL(?,password) WHERE "user".name=?'

s_set_group = 'UPDATE "group" SET topic=? WHERE "group".name=?'

s_set_config_user = 'INSERT OR REPLACE INTO "config_user" (config,value,' \
    'user_id,setter_id) VALUES((SELECT ?),(SELECT ?),(SELECT "user".id FROM ' \
    '"user" WHERE "user".name=?))'

s_set_config_group = 'INSERT OR REPLACE INTO "config_group" (config,value,' \
    'group_id,setter_id) VALUES((SELECT ?),(SELECT ?),(SELECT "group".id ' \
    'FROM "group" WHERE "group".name=?),(SELECT "user".id FROM "user" WHERE ' \
    '"user".name=?))'

s_del_user = 'DELETE FROM "user" WHERE "user".name=?'

s_del_user_acl = 'DELETE FROM "acl_user" WHERE "acl_user".acl=? AND ' \
    '"acl_user".user_id IN (SELECT "user".id FROM "user" WHERE "user".name=?)'

s_del_user_acl_all = 'DELETE FROM "acl_user" WHERE "acl_user".user_id IN ' \
    '(SELECT "user".id FROM "user" WHERE "user".name=?)'

s_del_group_acl = 'DELETE FROM "acl_group" WHERE "acl_group".acl=? AND ' \
    '"acl_group".user_id IN (SELECT "user".id FROM "user" WHERE ' \
    '"user".name=?) AND "acl_group".group_id IN (SELECT "group".id FROM ' \
    '"group" WHERE "group".name=?)'

s_del_group_acl_all = 'DELETE FROM "acl_group" WHERE "acl_group".group_id IN ' \
    '(SELECT "group".id FROM "group" WHERE "group".name=?)'

s_del_group = 'DELETE FROM "group" WHERE "group".name=?'


class ProtocolStorage:
    """ Basic protocol storage of DCP. Stores users, groups, user configs, and
    (soon) roster data. This class is so big because DCP's storage is all
    inter-dependent. """

    def __init__(self, dbname, schema='schema.sql'):
        self.database = Database(dbname)
        self.log = getLogger(__name__ + '.ProtocolStorage')

        with open(schema, 'r') as f:
            self.database.modify(f.read(), func='executescript')

    def get_user(self, name):
        c = self.database.read(s_get_user, (name,))
        return c.fetchone()

    def get_user_acl(self, name):
        c = self.database.read(get_user_acl, (name,))
        return c.fetchall()

    def get_user_config(self, name):
        c = self.database.read(s_get_user_config, (name,))
        return c.fetchall()

    def get_group(self, name):
        c = self.database.read(s_get_group, (name,)),
        return c.fetchone()

    def get_group_acl(self, name):
        c = self.database.read(s_get_group_acl, (name,))
        return c.fetchall()

    def get_group_acl_user(self, name, username):
        c = self.database.read(s_get_group_acl_user, (name,username))
        return c.fetchall()

    def get_group_config(self, name):
        c = self.database.read(s_get_group_config, (name,))
        return c.fetchall()

    def create_user(self, name, gecos, password):
        self.log.critical('creating user')
        c = self.database.modify(s_create_user,
                             (name, gecos, password))
        self.log.critical('executed with', name, gecos, password)
        return c

    def create_group(self, name, topic):
        return self.database.modify(s_create_group, (name, topic))

    def create_user_acl(self, name, acl, setter=None, reason=None):
        return self.database.modify(s_create_user_acl, (acl, name, reason))

    def create_group_acl(self, name, username, acl, setter=None, reason=None):
        return self.database.modify(s_create_group_acl,
                                (acl, name, username, setter, reason))

    def set_user(self, name, *, gecos=None, password=None):
        return self.database.modify(s_set_user, (gecos, password, name))

    def set_group(self, name, *, topic=None):
        return self.database.modify(s_set_group, (topic, name))

    def set_config_user(self, name, config, value=None, setter=None):
        return self.database.modify(s_set_config_user, (config, value, name))

    def create_config_user(self, name, config, value=None, setter=None):
        return self.set_config_user(name, config, value, setter)

    def set_config_group(self, name, username, config, value=None, setter=None):
        return self.database.modify(s_set_config_group,
                                (config, value, name, username))

    def create_config_group(self, name, username, config, value=None, setter=None):
        return self.set_config_group(c)

    def del_user(self, name):
        return self.database.modify(s_del_user, (name,))

    def del_user_acl(self, name, acl):
        return self.database.modify(s_del_user_acl, (acl,name))

    def del_user_acl_all(self, name):
        return self.database.modify(s_del_user_acl_all, (name,))

    def del_group_acl(self, name, username, acl):
        return self.database.modify(s_del_group_acl, (acl, username, name))

    def del_group_acl_all(self, name):
        return self.database.modify(s_del_group_acl_all, (name,))

    def del_group(self, name):
        return self.database.modify(s_del_group, (name,))


# The pool of cached DCP storage objects
proto_storage_pool = queue.Queue()

# The executor itself
proto_storage_executor = ThreadPoolExecutor(32)


class AsyncStorage:
    def __init__(self, storeclass, dbname):
        self.storeclass = storeclass
        self.dbname = dbname

    def run_callback(self, method_call, *args):
        try:
            storage = proto_storage_pool.get_nowait()
        except queue.Empty:
            storage = self.storeclass(self.dbname)

        try:
            method_call = getattr(storage, method_call)
            return method_call(*args)
        finally:
            # Place back into the pool
            proto_storage_pool.put(storage)

    def __getattr__(self, attr):
        loop = asyncio.get_event_loop()
        ret = partial(loop.run_in_executor, proto_storage_executor,
                      self.run_callback, attr)

        setattr(self, attr, ret)
        return ret
