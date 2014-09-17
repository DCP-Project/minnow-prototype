# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio
import sqlite3
import queue

from server.storage.sqlite import queries, atomic
from logging import getLogger


class ProtocolStorage:
    """ Basic protocol storage of DCP. Stores users, groups, user properties,
    and (soon) roster data. This class is so big because DCP's storage is all
    inter-dependent. """

    schema_file = 'server/storage/sqlite/schema.sql'

    def __init__(self, dbname):
        self.database = atomic.Database(dbname)
        self.log = getLogger(__name__ + '.ProtocolStorage')

        with open(self.schema_file, 'r') as f:
            self.database.modify(f.read(), func='executescript')

    def get_user(self, name):
        c = self.database.read(queries.s_get_user, (name,))
        return c.fetchone()

    def get_user_acl(self, name):
        c = self.database.read(queries.s_get_user_acl, (name,))
        return c.fetchall()

    def get_user_property(self, name):
        c = self.database.read(queries.s_get_user_property, (name,))
        return c.fetchall()

    def get_group(self, name):
        c = self.database.read(queries.s_get_group, (name,)),
        return c.fetchone()

    def get_group_acl(self, name):
        c = self.database.read(queries.s_get_group_acl, (name,))
        return c.fetchall()

    def get_group_acl_user(self, name, username):
        c = self.database.read(queries.s_get_group_acl_user, (name, username))
        return c.fetchall()

    def get_group_property(self, name):
        c = self.database.read(queries.s_get_group_property, (name,))
        return c.fetchall()

    def create_user(self, name, gecos, password):
        self.log.critical('creating user')
        c = self.database.modify(queries.s_create_user,
                                 (name, gecos, password))
        self.log.critical('executed with', name, gecos, password)
        return c

    def create_group(self, name, topic):
        return self.database.modify(queries.s_create_group, (name, topic))

    def create_user_acl(self, name, acl, setter=None, reason=None):
        return self.database.modify(queries.s_create_user_acl,
                                    (acl, name, reason))

    def create_group_acl(self, name, username, acl, setter=None, reason=None):
        return self.database.modify(queries.s_create_group_acl,
                                    (acl, name, username, setter, reason))

    def create_property_user(self, name, property, value=None, setter=None):
        return self.database.modify(queries.s_create_property_user,
                                    (property, value, name, setter))

    def create_property_group(self, name, property, value=None, setter=None):
        return self.database.modify(queries.s_create_property_group,
                                    (property, value, name, setter))

    def create_roster_user(self, name, user, alias=None, group_tag=None):
        return self.database.modify(queries.s_create_roster_user,
                                    (name, user, alias, group_tag))

    def create_roster_group(self, name, user, alias=None, group_tag=None):
        return self.database.modify(queries.s_create_roster_group,
                                    (name, user, alias, group_tag))

    def set_user(self, name, *, gecos=None, password=None):
        return self.database.modify(queries.s_set_user,
                                    (gecos, password, name))

    def set_group(self, name, *, topic=None):
        return self.database.modify(queries.s_set_group, (topic, name))

    def set_property_user(self, name, property, value=None, setter=None):
        return self.database.modify(queries.s_set_property_user,
                                    (value, property, name))

    def set_property_group(self, name, property, value=None, setter=None):
        return self.database.modify(queries.s_set_property_group,
                                    (value, property, name))

    def set_roster_user(self, name, *, alias=None, group_tag=None,
                        blocked=None):
        return self.database.modify(queries.s_set_roster_user,
                                    (alias, group_tag, blocked, name))

    def set_roster_group(self, name, *, alias=None, group_tag=None):
        return self.database.modify(queries.s_set_roster_group,
                                    (alias, group_tag, blocked, name))

    def del_user(self, name):
        return self.database.modify(queries.s_del_user, (name,))

    def del_user_acl(self, name, acl):
        return self.database.modify(queries.s_del_user_acl, (acl, name))

    def del_user_acl_all(self, name):
        return self.database.modify(queries.s_del_user_acl_all, (name,))

    def del_group_acl(self, name, username, acl):
        return self.database.modify(queries.s_del_group_acl,
                                    (acl, username, name))

    def del_group_acl_all(self, name):
        return self.database.modify(queries.s_del_group_acl_all, (name,))

    def del_group(self, name):
        return self.database.modify(queries.s_del_group, (name,))

    def del_property_user(self, name, property):
        return self.database.modify(queries.s_del_property_user,
                                    (property, name))

    def del_property_group(self, name, property):
        return self.database.modify(queries.s_del_property_group,
                                    (property, name))

    def del_roster_user(self, name, username):
        return self.database.modify(queries.s_del_roster_user,
                                    (name, username))

    def del_roster_group(self, name, group):
        return self.database.modify(queries.s_del_roster_group,
                                    (name, group))
