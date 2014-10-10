# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import time
from collections import defaultdict, namedtuple

from server.storage.abstractor import GroupAbstractor
from server.storageset import StorageSet, StorageItem
from server.property import GroupPropertySet
from server.acl import GroupACLSet

from server.user import User
from server.errors import *


GroupAbstractor = GroupAbstractor.__subclasses__()[0]

MembershipKey = namedtuple('MembershipKey', ('user', 'group'))


class MembershipData:

    def __init__(self):
        pass


class GroupData(StorageItem):

    """ Like an IRC channel """

    def __init__(self, server, name, topic=None, property=None, time_=None):
        if not name[0] == '#':
            name = '#{}'.format(name)

        if property is None:
            property = GroupPropertySet(server, name)

        members = dict()

        self.acl = GroupACLSet(group)

        if time_ is None:
            time = round(time.time())

        super().__init__(**locals())

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
            'time': [str(self.time)],
            'topic': [self.topic if self.topic else ''],
        }
        user.send(self, user, 'group-info', kval)

        kval = {
            'users': [u.user.name for u in self.members.keys()],
        }

        user.send_multipart(self, user, 'group-names', ('users',), kval)

    def member_del(self, user, reason=None):
        member = MembershipKey(user, self)
        if member not in self.members:
            raise GroupRemovalError('Nonexistent user {} removed'.format(
                user.name))

        del self.members[member], user.members[member]

    def member_has(self, user):
        member = MembershipKey(user, self)
        return member in self.members

    def member_get(self, user):
        member = MembershipKey(user, self)
        return self.members.get(member)

    def message(self, source, message):
        # TODO various ACL checks
        if isinstance(source, User) and not self.has_member(source):
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


class GroupSet(StorageSet):

    eager = True
    check_db_fail = False  # XXX

    def __init__(self, server, name):
        self.server = server
        super().__init__(GroupData, GroupAbstractor(server.proto_store))

    @asyncio.coroutine
    def add(self, group, topic=None):
        yield from super().add(group, topic)

    @asyncio.coroutine
    def _add_db(self, group, topic=None):
        yield from super()._add_db(group, topic)

    @asyncio.coroutine
    def set(self, group, topic=None):
        yield from super().set(group, topic)

    @asyncio.coroutine
    def _set_db(self, group, topic=None):
        yield from super()._set_db(group, topic)

    @asyncio.coroutine
    def delete(self, group):
        yield from super().delete(group)

    @asyncio.coroutine
    def _delete_db(self, group):
        yield from super()._delete_db(group)
