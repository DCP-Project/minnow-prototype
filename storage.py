import asyncio
import sqlite3
from collections import OrderedDict
from concurrent.futures import Future
from logging import getLogger
from multiprocessing import Queue, Manager
from multiprocessing.pool import ThreadPool
from threading import Lock, Thread
from uuid import uuid4


class Counter:
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


waiting = Lock()
accessing = Lock()
nreaders = Counter()


class AsyncSafeRow:
    def __init__(self, cursor, row):
        self.contents = OrderedDict()
        for index, colname in enumerate(cursor.description):
            self.contents[colname[0]] = row[index]

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.contents[self.contents.keys[item]]
        else:
            return self.contents[item]


class Database:
    def __init__(self, name='store.db'):
        self.conn = sqlite3.connect(name)
        self.conn.row_factory = AsyncSafeRow

    def modify(self, *data):
        with waiting:
            accessing.acquire()

        try:
            with self.conn:
                return self.conn.execute(*data)
        finally:
            accessing.release()

    def read(self, *data):
        with waiting:
            val = nreaders.inc()

            if val == 1:
                accessing.acquire()

        try:
            return self.conn.execute(*data)
        finally:
            val = nreaders.dec()
            if val == 0:
                accessing.release()

# Statements
s_get_user = 'SELECT "user".* FROM "user" WHERE "name"=?'

s_get_user_acl = 'SELECT "acl_user".* FROM "acl_user","user" WHERE ' \
    '"user".name=? AND "acl_user".user_id="user".id'

s_get_user_config = 'SELECT "config_user".* FROM "config_user","user" WHERE ' \
    '"user".name=? AND "config_user".user_id="user".id'

s_get_group = 'SELECT "group".* FROM "group" WHERE "name"=?'

s_get_group_acl = 'SELECT "acl_group".*,"user".name AS username FROM ' \
    '"acl_group","user","group" WHERE "group".name=? AND "group".id=' \
    '"acl_group".group_id AND "user".id="acl_group".user_id'

s_get_group_acl_user = 'SELECT "acl_group".* FROM "acl_group","user" WHERE ' \
    '"group".name=? AND "user".name=? AND "group".id="acl_group".group_id ' \
    'AND "user".id="acl_user".user_id'

s_get_group_config = '*SELECT "config_group".*,"user".name AS username FROM ' \
    '"config_group","user","group" WHERE "group".name=? AND ' \
    '"group".id="config_group".group_id AND "user".id="config_group".user_id'

s_create_user = 'INSERT INTO "user" (name,gecos,password) VALUES (?,?,?)'

s_create_group = 'INSERT INTO "group" (name) VALUES(?)'

s_create_user_acl = 'INSERT INTO "acl_user" (acl,user_id) SELECT ?,"user".id ' \
    'FROM "user" WHERE "user".name=?'

s_create_group_acl = 'INSERT INTO "acl_group" (acl,group_id,user_id,' \
    'setter_id) VALUES((SELECT ?),(SELECT "group".id FROM "group" WHERE ' \
    '"group".name=?),(SELECT "user".id FROM "user" WHERE "user".name=?),' \
    '(SELECT "user".id FROM "user" WHERE "user".name=?))'

s_set_user = 'UPDATE "user" SET gecos=IFNULL(?,gecos),password=' \
    'IFNULL(?,password) WHERE "user".name=?'

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


class DCPStorage:
    def __init__(self, dbname, schema='schema.sql'):
        self.conn = Database(dbname)
        self.log = getLogger('DCPStorage')

        with open(schema, 'r') as f:
            self.conn.executescript(''.join(f.readlines()))

    #def __del__(self):
    #    self.conn.close()

    #def close(self):
    #    self.conn.commit()
    #    self.conn.close()

    def get_user(self, name):
        c = self.conn.read(s_get_user, (name,))
        return c.fetchone()

    def get_user_acl(self, name):
        c = self.conn.read(get_user_acl, (name,))
        return c.fetchall()

    def get_user_config(self, name):
        c = self.conn.read(s_get_user_config, (name,))
        return c.fetchall()

    def get_group(self, name):
        c = self.conn.read(s_get_group, (name,)),
        return c.fetchone()

    def get_group_acl(self, name):
        c = self.conn.read(s_get_group_acl, (name,))
        return c.fetchall()

    def get_group_acl_user(self, name, username):
        c = self.conn.read(s_get_group_acl_user, (name,username))
        return c.fetchall()

    def get_group_config(self, name):
        c = self.conn.read(s_get_group_config, (name,))
        return c.fetchall()

    def create_user(self, name, gecos, password):
        self.log.critical('creating user')
        c = self.conn.modify(s_create_user,
                             (name, gecos, password))
        self.log.critical('executed with', name, gecos, password)
        return c

    def create_group(self, name):
        return self.conn.modify(s_create_group, (name,))

    def create_user_acl(self, name, acl, setter=None):
        return self.conn.modify(s_create_user_acl, (acl,name))

    def create_group_acl(self, name, username, acl, setter=None):
        return self.conn.modify(s_create_group_acl,
                                (acl, name, username, setter))

    def set_user(self, name, *, gecos=None, password=None):
        return self.conn.modify(s_set_user, (gecos, password))

    def set_config_user(self, name, config, value=None, setter=None):
        return self.conn.modify(s_set_config_user, (config, value, name))

    def create_config_user(self, name, config, value=None, setter=None):
        return self.set_config_user(name, config, value, setter)

    def set_config_group(self, name, username, config, value=None, setter=None):
        return self.conn.modify(s_set_config_group,
                                (config, value, name, username))
    
    def create_config_group(self, name, username, config, value=None, setter=None):
        return self.set_config_group(c)

    def del_user(self, name):
        return self.conn.modify(s_del_user, (name,))

    def del_user_acl(self, name, acl):
        return self.conn.modify(s_del_user_acl, (acl,name))

    def del_user_acl_all(self, name):
        return self.conn.modify(s_del_user_acl_all, (name,))

    def del_group_acl(self, name, username, acl):
        return self.conn.modify(s_del_group_acl, (acl, username, name))

    def del_group_acl_all(self, name):
        return self.conn.modify(s_del_group_acl_all, (name,))

    def del_group(self, name):
        return self.conn.modify(s_del_group, (name,))


class EngineNotStartedException(RuntimeError):
    pass


def db_process(store_name, call, future, *args):
    storage = DCPStorage(store_name)
    log = getLogger('database worker thread')

    try:
        meth = getattr(storage, call)
        res = meth(*args)
        if future:
            future.set_result(res)
    except AttributeError as ex:
        log.exception('invalid call')
        if future:
            future.set_result(None)
    except e:
        log.exception('while running %s', call)
        if future:
            future.set_exception(e)


class DCPAsyncStorage:
    def __init__(self, dbname='store.db'):
        self.pool = ThreadPool()
        self.dbname = dbname

    def get_user(self, name):
        future = Future()
        self.pool.apply_async(db_process, self.dbname, future, 'get_user', name)
        return asyncio.wrap_future(future)

    def create_user(self, name, gecos, password):
        self.pool.apply_async(db_process, self.dbname, None, 'create_user', name, gecos, password)
