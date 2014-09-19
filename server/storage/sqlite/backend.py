# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import sqlite3
import pathlib

from server.storage import abstractor
from server.storage.sqlite import queries, atomic
from logging import getLogger


class ProtocolStorage(abstractor.ProtocolStorage):

    """ Basic protocol storage of DCP. Stores users, groups, user properties,
    and roster data.
    """

    BASEPATH = pathlib.Path('server', 'storage', 'sqlite')
    SCHEMA_VER = 2

    _initdb = False
    _init_lock = Lock()

    def __init__(self, dbname):
        super().__init__()

        self.database = atomic.Database(dbname)

    def sql_file(self, path):
        with path.open() as f:
            self.database.modify(f.read(), func='executescript')


class UserAbstractor(abstractor.UserAbstractor):

    def add(self, name, gecos, password):
        self.log.critical('creating user')
        c = self.storage.database.modify(queries.s_create_user,
                                         (name, gecos, password))
        self.log.critical('executed with', name, gecos, password)
        return c

    def get_one(self, name):
        c = self.storage.database.read(queries.s_get_user, (name,))
        return c.fetchone()

    def get_all(self):
        raise NotImplementedError()

    def set(self, name, gecos=None, password=None):
        return self.storage.database.modify(queries.s_set_user,
                                            (gecos, password, name))

    def delete(self, name):
        return self.storage.database.modify(queries.s_del_user, (name,))


class GroupAbstractor(abstractor.GroupAbstractor):

    def add(self, name, topic):
        return self.storage.database.modify(
            queries.s_create_group, (name, topic))

    def get_one(self, name):
        c = self.storage.database.read(queries.s_get_group, (name,)),
        return c.fetchone()

    def get_all(self):
        raise NotImplementedError()

    def set(self, name, topic=None):
        return self.storage.database.modify(queries.s_set_group, (topic, name))

    def delete(self, name):
        return self.storage.database.modify(queries.s_del_group, (name,))


class UserACLAbstractor(abstractor.UserACLAbstractor):

    def add(self, name, acl, setter=None, reason=None):
        return self.storage.database.modify(queries.s_create_user_acl,
                                            (acl, name, reason))

    def get_one(self, name, acl):
        raise NotImplementedError()

    def get_all(self, name):
        c = self.storage.database.read(queries.s_get_user_acl, (name,))
        return c.fetchall()

    def set(self, name, acl, setter=None, reason=None):
        try:
            self.delete(name, acl)
        except Exception:
            pass

        self.add(name, acl, setter, reason)

    def delete(self, name, acl):
        return self.storage.database.modify(
            queries.s_del_user_acl, (acl, name))

    def delete_all(self, name):
        return self.storage.database.modify(
            queries.s_del_user_acl_all, (name,))


class GroupACLAbstractor(abstractor.GroupACLAbstractor):

    def add(self, name, target, acl, setter=None, reason=None):
        return self.storage.database.modify(queries.s_create_group_acl,
                                            (acl, name, target, setter,
                                             reason))

    def get_one(self, name, target):
        c = self.storage.database.read(
            queries.s_get_group_acl_user, (name, target))
        return c.fetchall()

    def get_all(self, name):
        c = self.storage.database.read(queries.s_get_group_acl, (name,))
        return c.fetchall()

    def set(self, name, target, acl, setter=None, reason=None):
        try:
            self.delete(name, target, acl)
        except Exception:
            pass

        self.add(name, target, acl, setter=None, reason=None)

    def delete(self, name, target, acl):
        return self.storage.database.modify(queries.s_del_group_acl,
                                            (acl, target, name))

    def delete_all(self, name):
        return self.storage.database.modify(
            queries.s_del_group_acl_all, (name,))


class UserPropertyAbstractor(abstractor.UserPropertyAbstractor):

    def add(self, name, property, value=None, setter=None):
        return self.storage.database.modify(queries.s_create_property_user,
                                            (property, value, name, setter))

    def get_one(self, name, property):
        raise NotImplementedError()

    def get_all(self, name):
        c = self.storage.database.read(queries.s_get_user_property, (name,))
        return c.fetchall()

    def set(self, name, property, value=None, setter=None):
        return self.storage.database.modify(queries.s_set_property_user,
                                            (value, property, name))

    def delete(self, name, property):
        return self.storage.database.modify(queries.s_del_property_user,
                                            (property, name))


class GroupPropertyAbstractor(abstractor.GroupPropertyAbstractor):

    def add(self, name, property, value=None, setter=None):
        return self.storage.database.modify(queries.s_create_property_group,
                                            (property, value, name, setter))

    def get_one(self, name, property):
        raise NotImplementedError()

    def get_all(self, name):
        c = self.storage.database.read(queries.s_get_group_property, (name,))
        return c.fetchall()

    def set(self, name, property, value=None, setter=None):
        return self.storage.database.modify(queries.s_set_property_group,
                                            (value, property, name))

    def delete(self, name, property):
        return self.storage.database.modify(queries.s_del_property_group,
                                            (property, name))


class RosterUserAbstractor(abstractor.RosterUserAbstractor):

    def add(self, name, user, alias=None, group_tag=None):
        return self.storage.database.modify(queries.s_create_roster_user,
                                            (name, user, alias, group_tag))

    def get_one(self, name, user):
        raise NotImplementedError()

    def get_all(self, name):
        c = self.storage.database.read(queries.s_get_roster_user, (name,))
        return c.fetchall()

    def set(self, name, alias=None, group_tag=None, blocked=None):
        return self.storage.database.modify(queries.s_set_roster_user,
                                            (alias, group_tag, blocked, name))

    def delete(self, name, target):
        return self.storage.database.modify(queries.s_del_roster_user,
                                            (name, target))


class RosterGroupAbstractor(abstractor.RosterGroupAbstractor):

    def add(self, name, group, alias=None, group_tag=None):
        return self.storage.database.modify(queries.s_create_roster_group,
                                            (name, group, alias, group_tag))

    def get_one(self, name, group):
        raise NotImplementedError()

    def get_all(self, name):
        c = self.storage.database.read(queries.s_get_roster_group, (name,))
        return c.fetchall()

    def set(self, name, alias=None, group_tag=None):
        return self.storage.database.modify(queries.s_set_roster_group,
                                            (alias, group_tag, blocked, name))

    def delete(self, name, group):
        return self.storage.database.modify(queries.s_del_roster_group,
                                            (name, group))


class ACLAbstractor(abstractor.ACLAbstractor):

    def add(self, name, target, acl, setter=None, reason=None):
        if name[0] == '#':
            return GroupACLAbstractor.add(self, name, target, acl, setter, 
                                          reason)
        else:
            return UserACLAbstractor.add(self, name, acl, setter, reason)

    def get_one(self, name, acl):
        if name[0] == '#':
            GroupACLAbstractor.get_one(self, name, acl)
        else:
            UserACLAbstractor.get_one(self, name, acl)

    def get_all(self, name):
        if name[0] == '#':
            return GroupACLAbstractor.get_all(self, name)
        else:
            return UserACLAbstractor.get_all(self, name)

    def set(self, name, target, acl, setter=None, reason=None):
        if name[0] == '#':
            return GroupACLAbstractor.set(self, name, target, acl, setter,
                                          reason)
        else:
            return UserACLAbstractor.set(self, name, acl, setter, reason)

    def delete(self, name, target, acl):
        if name[0] == '#':
            return GroupACLAbstractor.delete(self, name, target, acl)
        else:
            return UserACLAbstractor.delete(self, name, target, acl)


class PropertyAbstractor(abstractor.PropertyAbstractor):

    def add(self, name, property, value=None, setter=None):
        if name[0] == '#':
            return GroupPropertyAbstractor.add(self, name, property, value,
                                               setter)
        else:
            return UserPropertyAbstractor.add(self, name, property, value,
                                              setter)

    def get_one(self, name):
        if name[0] == '#':
            return GroupPropertyAbstractor.get_one(self, name)
        else:
            return UserPropertyAbstractor.get_one(self, name)

    def get_all(self, name):
        if name[0] == '#':
            return GroupPropertyAbstractor.get_all(self, name)
        else:
            return UserPropertyAbstractor.get_all(self, name)

    def set(self, name, property, value=None, setter=None):
        if name[0] == '#':
            return GroupPropertyAbstractor.set(self, name, property, value,
                                               setter)
        else:
            return UserPropertyAbstractor.set(self, name, property, value,
                                              setter)

    def delete(self, name, property):
        if name[0] == '#':
            return GroupPropertyAbstractor.delete(self, name, property)
        else:
            return UserPropertyAbstractor.delete(self, name, property)


class RosterAbstractor(abstractor.RosterAbstractor):

    def add(self, name, group, alias=None, group_tag=None, pending=None):
        if name[0] == '#':
            return RosterGroupAbstractor.add(self, name, group, alias,
                                             group_tag)
        else:
            return RosterUserAbstractor.add(self, name, group, alias,
                                            group_tag)

    def get_one(self, name):
        if name[0] == '#':
            return RosterGroupAbstractor.get_one(self, name)
        else:
            return RosterUserAbstractor.get_one(self, name)

    def get_all(self, name):
        if name[0] == '#':
            return RosterGroupAbstractor.get_all(self, name)
        else:
            return RosterUserAbstractor.get_all(self, name)

    def set(self, name, alias=None, group_tag=None, blocked=None,
            pending=None):
        if name[0] == '#':
            return RosterGroupAbstractor.set(self, name, alias, group_tag)
        else:
            return RosterUserAbstractor.set(self, name, alias, group_tag,
                                            blocked)

    def delete(self, name, target):
        if name[0] == '#':
            return RosterGroupAbstractor.delete(self, name, target)
        else:
            return RosterUserAbstractor.delete(self, name, target)
