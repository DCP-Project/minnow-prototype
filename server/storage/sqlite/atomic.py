# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import sqlite3

from collections import defaultdict
from threading import Lock


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

    def __init__(self, dbname='data/store.db'):
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
