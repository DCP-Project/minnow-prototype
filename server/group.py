# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import time
from collections import defaultdict, namedtuple

from server.user import User
from server.parser import MAXFRAME
from server.acl import GroupACLSet
from server.property import GroupPropertySet
from server.errors import *


MembershipKey = namedtuple('MembershipKey', ('user', 'group'))


class MembershipData:

    def __init__(self, acl):
        self.user = user
        self.group = group

        self.acl = acl


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

        self.members = dict() 

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
        member = MembershipData(user, self)
        if member in self.members:
            # It's all about membership
            raise GroupAdditionError('Duplicate user added: {}'.format(
                user.name))

        data = MembershipData(None)
        self.members[member] = user.members[member] = data

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
            'users': [u.user.name for u in self.members.keys()],
        }

        # TODO use multipart
        user.send_multipart(self, user, 'group-names', ('users',), kval)

    def member_del(self, user, reason=None):
        member = MembershipKey(user, self)
        if member not in self.members:
            raise GroupRemovalError('Nonexistent user {} removed'.format(
                user.name))

        del self.members[member], user.members[member]

    def has_member(self, user):
        member = MembershipKey(user, self)
        return member in self.members

    def message(self, source, message):
        # TODO various ACL checks
        if isinstance(source, User) and not self.has_user(source):
            self.server.error(source, 'message', 'You aren\'t in that group',
                              False)
            return

        kval = defaultdict(list)
        kval['body'] = message

        self.send(source, self, 'message', kval, [source])

    def send(self, source, target, command, kval=None, filter=[]):
        for (user, group) in self.members.keys():
            if user in filter:
                continue

            user.send(source, target, command, kval)

    def send_multipart(self, source, target, command, keys=[], kval=None,
                       filter=[]):
        for (user, group) in self.members.keys():
            if user in filter:
                continue

            user.send_multipart(source, target, command, keys, kval)
