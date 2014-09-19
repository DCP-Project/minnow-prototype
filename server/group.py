# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import time
from collections import defaultdict

from server.user import User
from server.parser import MAXFRAME
from server.acl import GroupACLSet
from server.property import GroupPropertySet
from server.errors import *


class Group:

    """ Like an IRC channel """

    def __init__(self, server, name, topic=None, acl=None, property=None,
                 ts=None):
        self.server = server
        self.name = name
        self._topic = topic

        if acl is None:
            acl = GroupACLSet(server, name)

        self.acl = acl

        if property is None:
            property = GroupPropertySet(server, name)

        self.property = property

        self.users = set()

        self.ts = None

        if self.ts is None:
            self.ts = round(time.time())

        if not self.name[0] == '#':
            self.name = '#' + self.name

    @property
    def topic(self):
        return self._topic

    @topic.setter
    def topic(self, value):
        self._topic = value

        asyncio.async(self.server.proto_store.set_group(self.name.lower(),
                      topic=value))

    def member_add(self, user, reason=None):
        if user in self.users:
            raise GroupAdditionError('Duplicate user added: {}'.format(
                user.name))

        user.groups.add(self)
        self.users.add(user)

        kval = dict()
        if reason:
            kval['reason'] = [reason]

        self.send(user, self, 'group-enter', kval)

        # Burst the channel info
        kval = {
            'time': [str(self.ts)],
            'topic': [self.topic if self.topic else ''],
        }
        user.send(self, user, 'group-info', kval)

        kval = {
            'users': list(self.users),
        }

        # TODO use multipart
        user.send_multipart(self, user, 'group-names', ('users',), kval)

    def member_del(self, user, reason=None, permanent=False):
        if user not in self.users:
            raise GroupRemovalError('Nonexistent user {} removed'.format(
                user.name))

        self.users.remove(user)
        user.groups.remove(self)

    def message(self, source, message):
        # TODO various ACL checks
        if isinstance(source, User) and source not in self.users:
            self.server.error(source, 'message', 'You aren\'t in that group',
                              False)
            return

        kval = defaultdict(list)
        kval['body'] = message

        self.send(source, self, 'message', kval, [source])

    def send(self, source, target, command, kval=None, filter=[]):
        for user in self.users:
            if user in filter:
                continue

            user.send(source, target, command, kval)

    def send_multipart(self, source, target, command, keys=[], kval=None,
                       filter=[]):
        for user in self.users:
            if user in filter:
                continue

            user.send_multipart(source, target, command, keys, kval)
