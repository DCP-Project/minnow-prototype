# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import abc
import pathlib
from threading import Lock


class StorageAbstractor(metaclass=abc.ABCMeta):

    """ The base storage abstraction class. All storage abstractors must
    conform to this interface at the minimum. """

    def __init__(self, storage):
        self.storage = storage

    @abc.abstractmethod
    def add(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def set(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def get(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def delete(self, *args, **kwargs):
        pass


# If you implement your own backend, you must conform to the below classes.

class UserAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def add(self, name, gecos, password, avatar=None):
        pass

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def set(self, name, gecos=None, password=None, avatar=None):
        pass

    @abc.abstractmethod
    def delete(self, name):
        pass


class GroupAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def add(self, name, topic):
        pass

    @abc.abstractmethod
    def set(self, name, topic=None):
        pass

    @abc.abstractmethod
    def delete(self, name):
        pass


class UserACLAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def add(self, name, acl, setter=None, reason=None):
        pass

    @abc.abstractmethod
    def set(self, name, acl, setter=None, reason=None):
        pass

    @abc.abstractmethod
    def delete(self, name, acl):
        pass


class GroupACLAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def get_user(self, name, target):
        pass

    @abc.abstractmethod
    def add(self, name, target, acl, setter=None, reason=None):
        pass

    @abc.abstractmethod
    def set(self, name, target, acl, setter=None, reason=None):
        pass

    @abc.abstractmethod
    def delete(self, name, target, acl):
        pass

    @abc.abstractmethod
    def delete_all(self, name):
        pass


class UserPropertyAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def add(self, name, property, value=None, setter=None):
        pass

    @abc.abstractmethod
    def set(self, name, property, value=None, setter=None):
        pass

    @abc.abstractmethod
    def delete(self, name, property):
        pass

    @abc.abstractmethod
    def delete_all(self, name):
        pass


class GroupPropertyAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def add(self, name, property, value=None, setter=None):
        pass

    @abc.abstractmethod
    def set(self, name, property, value=None, setter=None):
        pass

    @abc.abstractmethod
    def delete(self, name, property):
        pass


class RosterUserAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def add(self, name, user, alias=None, group_tag=None):
        pass

    @abc.abstractmethod
    def set(self, name, alias=None, group_tag=None, blocked=None):
        pass

    @abc.abstractmethod
    def delete(self, name, target):
        pass


class RosterGroupAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def add(self, name, group, alias=None, group_tag=None):
        pass

    @abc.abstractmethod
    def set(self, name, alias=None, group_tag=None):
        pass

    @abc.abstractmethod
    def delete(self, name, group):
        pass


class RosterAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def add(self, name, user, alias=None, group_tag=None, pending=None):
        pass

    @abc.abstractmethod
    def set(self, name, alias=None, group_tag=None, blocked=None,
            pending=None):
        pass

    @abc.abstractmethod
    def delete(self, name, target):
        pass


class ACLAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def add(self, name, target, acl, setter=None, reason=None):
        pass

    @abc.abstractmethod
    def set(self, name, target, acl, setter=None, reason=None):
        pass

    @abc.abstractmethod
    def delete(self, name, target, acl):
        pass


class PropertyAbstractor(StorageAbstractor, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get(self, name):
        pass

    @abc.abstractmethod
    def add(self, name, property, value=None, setter=None):
        pass

    @abc.abstractmethod
    def set(self, name, property, value=None, setter=None):
        pass

    @abc.abstractmethod
    def delete(self, name, property):
        pass


class BaseProtocolStorage(metaclass=abc.ABCMeta):

    BASEPATH = pathlib.Path('server', 'storage')

    _initdb = False
    _init_lock = Lock()

    def __init__(self, *args, **kwargs):
        self.log = getLogger(__name__ + '.ProtocolStorage')

        with self._init_lock:
            if not self._initdb:
                self.initalise()
                self._initdb = True

    def initalise(self):
        """ Initalise the DB and upgrade the schema

        The below commands are written to be portable enough to any DB engine.
        """

        self.sql_file(self.BASEPATH.joinpath('schema.sql'))

        # Upgrade the schema if needs be
        c = self.database.read('SELECT "version" FROM "version"')
        schema_ver = c.fetchone()['version']

        self.log.info('Present schema at %d', schema_ver)

        if schema_ver < self.SCHEMA_VER:
            for p in self.BASEPATH.joinpath('upgrade').rglob('*.sql'):
                ver = int(p.name[:-4])
                if ver >= schema_ver:
                    self.log.info('Upgrading schema to version %d', ver)
                    self.sql_file(p)

            self.database.modify('UPDATE "version" SET "version"=?',
                                 (self.SCHEMA_VER,))

    @abc.abstractmethod
    def sql_file(self, path):
        with path.open() as f:
            pass
