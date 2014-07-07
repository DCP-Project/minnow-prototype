import time
from collections import defaultdict

from errors import *
from user import User
from parser import MAXFRAME

class Group:
    """ Like an IRC channel """
    def __init__(self, name, topic=None, acl=None, config=None, ts=None):
        self.name = name
        self.topic = topic
        self.acl = acl
        self.config = config
        self.users = set()
        self.ts = None

        if self.acl is None:
            self.acl = defaultdict(list)

        if self.config is None:
            self.config = dict()

        if self.ts is None:
            self.ts = round(time.time())

        if not self.name.startswith('#'):
            self.name = '#' + self.name

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
            'time' : [str(self.ts)],
            'topic' : [self.topic if self.topic else ''],
        }
        user.send(self, user, 'group-info', kval)

        kval = {
            'users' : []
        }

        d_tlen = tlen = 500 # Probably too much... but good enough for now.
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
            'acl' : [],
        }
        user.send(self, user, 'acl-list', None)

    def member_del(self, user, reason=None, permanent=False):
        if user not in self.users:
            raise GroupRemovalError('Nonexistent user {} removed'.format(
                user.name))

        self.users.remove(user)
        user.groups.remove(self)

        kval = defaultdict(list)
        if not reason:
            reason = ['']

        kval['reason'].append(reason)

        if permanent:
            kval['quit'] = '*'

        self.send(self, user, 'group-exit', kval)

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
