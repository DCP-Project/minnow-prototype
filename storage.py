import asyncio
import sqlite3
from collections import OrderedDict
from logging import getLogger
from multiprocessing import Process, Queue, Manager
from threading import Thread, RLock
from uuid import uuid4

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

class DCPStorage:
    def __init__(self, dbname, schema='schema.sql'):
        self.conn = sqlite3.connect(dbname)
        self.conn.row_factory = AsyncSafeRow
        self.log = getLogger('DCPStorage')

        with open('schema.sql', 'r') as f:
            self.conn.executescript(''.join(f.readlines()))

    def __del__(self):
        self.conn.close()

    def close(self):
        self.conn.commit()
        self.conn.close()

    def get_user(self, name):
        self.log.critical('get user')
        c = self.conn.execute(s_get_user, (name,))
        return c.fetchone()

    def get_user_acl(self, name):
        c = self.conn.execute(get_user_acl, (name,))
        return c.fetchall()

    def get_user_config(self, name):
        c = self.conn.execute(s_get_user_config, (name,))
        return c.fetchall()

    def get_group(self, name):
        c = self.conn.execute(s_get_group, (name,)),
        return c.fetchone()

    def get_group_acl(self, name):
        c = self.conn.execute(s_get_group_acl, (name,))
        return c.fetchall()

    def get_group_acl_user(self, name, username):
        c = self.conn.execute(s_get_group_acl_user, (name,username))
        return c.fetchall()

    def get_group_config(self, name):
        c = self.conn.execute(s_get_group_config, (name,))
        return c.fetchall()

    def create_user(self, name, gecos, password):
        self.log.critical('creating user')
        with self.conn:
            self.log.critical('in context')
            c = self.conn.execute(s_create_user,
                                  (name, gecos, password))
            self.log.critical('executed with', name, gecos, password)
        self.log.critical('done')
        return c

    def create_group(self, name):
        with self.conn:
            c = self.conn.execute(s_create_group, (name,))
        return c

    def create_user_acl(self, name, acl, setter=None):
        with self.conn:
            c = self.conn.execute(s_create_user_acl, (acl,name))
        return c

    def create_group_acl(self, name, username, acl, setter=None):
        with self.conn:
            c = self.conn.execute(s_create_group_acl,
                                  (acl, name, username, setter))
        return c

    def set_user(self, name, *, gecos=None, password=None):
        with self.conn:
            c = self.conn.execute(s_set_user, (gecos, password))
        return c

    def set_config_user(self, name, config, value=None, setter=None):
        with self.conn:
            c = self.conn.execute(s_set_config_user, (config, value, name))
        return c

    def create_config_user(self, name, config, value=None, setter=None):
        return self.set_config_user(name, config, value, setter)

    def set_config_group(self, name, username, config, value=None, setter=None):
        with self.conn:
            c = self.conn.execute(s_set_config_group,
                                  (config, value, name, username))
        return c
    
    def create_config_group(self, name, username, config, value=None, setter=None):
        return self.set_config_group(c)

    def del_user(self, name):
        with self.conn:
            c = self.conn.execute(s_del_user, (name,))
        return c

    def del_user_acl(self, name, acl):
        c = self.conn.execute(s_del_user_acl, (acl,name))
        self.conn.commit()
        return c

    def del_user_acl_all(self, name):
        c = self.conn.execute('DELETE FROM "acl_user" WHERE ' \
                              '"acl_user".user_id IN (SELECT "user".id FROM ' \
                              '"user" WHERE "user".name=?)', (name,))
        self.conn.commit()
        return c

    def del_group_acl(self, name, username, acl):
        c = self.conn.execute('DELETE FROM "acl_group" WHERE "acl_group".acl=' \
                              '? AND "acl_group".user_id IN (SELECT ' \
                              '"user".id FROM "user" WHERE "user".name=?) ' \
                              'AND "acl_group".group_id IN (SELECT ' \
                              '"group".id FROM "group" WHERE "group".name=?)',
                              (acl, username, name))
        self.conn.commit()
        return c

    def del_group_acl_all(self, name):
        c = self.conn.execute('DELETE FROM "acl_group" WHERE ' \
                              '"acl_group".group_id IN (SELECT "group".id ' \
                              'FROM "group" WHERE "group".name=?)', (name,))
        self.conn.commit()
        return c

    def del_group(self, name):
        c = self.conn.execute('DELETE FROM "group" WHERE "group".name=?',
                              (name,))
        self.conn.commit()
        return c


class EngineNotStartedException(RuntimeError):
    pass


futures = dict()
flock = RLock()
requests = None
responses = None

def db_process(reqq, respq, store_name):
    storage = DCPStorage(store_name)
    log = getLogger('database worker process')

    while True:
        (rid, call, *args) = reqq.get()
        try:
            meth = getattr(storage, call)
            result = meth(*args)
            respq.put( (rid, result) )
        except AttributeError as ex:
            log.exception('invalid call')
            respq.put( (rid, None) )


def db_listen(respq, loop):
    while True:
        (rid, result) = respq.get()
        with flock:
            f = futures.pop(rid)
        if f and not f.cancelled():
            loop.call_soon_threadsafe(f.set_result, result)


class DCPAsyncStorage:
    def __init__(self, dbname):
        global requests, responses
        m = Manager()
        requests = m.Queue()
        responses = m.Queue()

        p = Process(target=db_process, name='minnow: Data process',
                    args=(requests, responses, dbname,) )
        p.start()
        t = Thread(target=db_listen, name='async store retrieval thread',
                   args=(responses, asyncio.get_event_loop(),) )
        t.start()

    def __make_rid(self):
        rid = uuid4()

        if rid in futures:
            raise RuntimeError('dupe')

        return rid

    def get_user(self, name, future):
        rid = self.__make_rid()
        with flock:
            futures[rid] = future

        requests.put( (rid, 'get_user', name) )

    def create_user(self, name, gecos, password):
        rid = self.__make_rid()
        with flock:
            futures[rid] = None

        requests.put( (rid, 'create_user', name, gecos, password) )
