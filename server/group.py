import time
from collections import defaultdict

from server.user import User
from server.parser import MAXFRAME
from server.acl import GroupACLSet
from server.property import GroupProperty
from server.errors import *


class Group:
    """ Like an IRC channel """
    def __init__(self, server, name, topic=None, acl=None, property=None,
                 ts=None):
        self.server = server
        self.name = name
        self._topic = topic
        self.acl = acl
        self.property = property
        self.users = set()
        self.ts = None

        self.callbacks = dict()

        if self.acl is None:
            self.acl = defaultdict(GroupACLSet)

        if self.property is None:
            self.property = GroupProperty()

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

        self.users.add(user)
        user.groups.add(self)

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
            'users': []
        }

        # TODO use multipart
        d_tlen = tlen = 500  # Probably too much... but good enough for now.
        for user2 in self.users:
            tlen += len(user2.name) + 1
            if tlen >= MAXFRAME:
                # Overflow... send what we have and continue
                user.send(self, user, 'group-names', kval)
                tlen = d_tlen + len(user2.name) + 1
                kval['users'] = []

            kval['users'].append(user2.name)

        # Burst what's left
        if len(kval['users']) > 0:
            user.send(self, user, 'group-names', kval)

        # Burst ACL's
        kval = {
            'acl': [],
        }
        user.send(self, user, 'acl-list', None)

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

    def call_later(self, name, delay, callback, *args):
        loop = asyncio.get_event_loop()
        self.callback[name] = loop.call_later(delay, callback, *args)
        return self.callback[name]

    def call_at(self, name, when, callback, *args):
        loop = asyncio.get_event_loop()
        self.callback[name] = loop.call_at(when, callback, *args)
        return self.callback[name]
