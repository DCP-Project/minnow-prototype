# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio

from time import time

from server.property import UserPropertySet
from server.acl import UserACLSet
from server.roster import Roster


class User:
    def __init__(self, server, name, gecos, password, acl=None, property=None,
                 roster=None, options=[]):
        self.server = server
        self.name = name
        self._gecos = gecos
        self._password = password

        if acl is None:
            self.acl = UserACLSet(server, name)

        self.acl = acl

        if property is None:
            property = UserPropertySet(server, name)

        if roster is None:
            roster = Roster(server, name)

        self.property = property
        self.roster = roster
        self.options = options  # TODO

        self.sessions = set()
        self.groups = set()

        self.signon = round(time())

    @property
    def gecos(self):
        return self._gecos

    @gecos.setter
    def gecos(self, value):
        self._gecos = value
        asyncio.async(self.server.proto_store.set_user(self.name.lower(),
                      gecos=value))

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value

        asyncio.async(self.server.proto_store.set_user(self.name.lower(),
                      password=value))

    def send(self, source, target, command, kval=None):
        if kval is None:
            kval = {}

        for proto in self.sessions:
            proto.send(source, target, command, kval)

    def send_multipart(self, source, target, command, keys=[], kval=None):
        for proto in self.sessions:
            proto.send_multipart(source, target, command, keys, kval)

    def message(self, source, message):
        self.send(source, self, 'message', {'body': message})

    def __hash__(self):
        return hash((hash(self.name), hash(self.gecos)))
