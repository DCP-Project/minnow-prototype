# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio
import enum
from time import time
from collections import defaultdict


class ACL:
    __slots__ = ['setter', 'reason', 'time']

    def __init__(self, setter=None, reason=None, time_=None):
        self.setter = setter
        self.reason = reason
        if time_ is None:
            time_ = round(time())

        self.time = time_


class UserACLValues(enum.Enum):
    user_auspex = 'user:auspex'
    user_register = 'user:register'
    user_revoke = 'user:revoke'
    user_grant = 'user:grant'
    user_disconnect = 'user:disconnect'
    user_ban = 'user:ban'

    group_auspex = 'group:auspex'
    group_register = 'group:register'
    group_override = 'group:override'
    group_revoke = 'group:revoke'
    group_ban = 'group:ban'

    # Prohibition ACL's
    ban_banned = 'ban:banned'
    ban_usermessage = 'ban:usermessage'


class GroupACLValues(enum.Enum):
    user_kick = 'user:kick'
    user_ban = 'user:ban'
    user_mute = 'user:mute'
    user_voice = 'user:voice'

    user_owner = 'user:owner'
    user_admin = 'user:admin'
    user_op = 'user:op'

    group_topic = 'group:topic'
    group_property = 'group:property'
    group_clear = 'group:clear'

    # Blanket grant
    grant_all = 'grant:*'

    # Prohibition ACL's
    ban_banned = 'ban:banned'
    ban_mute = 'ban:mute'


class UserACLSet:

    __slots__ = ['server', 'user', 'acl_map']

    def __init__(self, server, user, acl_data=[]):
        # NOTE - we use acl_data here separate instead of getting it ourselves
        # because __init__ being a coroutine is probably dodgy.
        self.server = server
        self.user = user.lower()
        self.acl_map = dict()

        if not acl_data:
            return

        for acl in acl_data:
            self._add_nocommit(acl['acl'], acl['setter'], acl['reason'],
                               acl['timestamp'])

    def __iter__(self):
        return self.acl_map.items()

    def has_acl(self, acl):
        return acl in self.acl_map

    def has_any(self, acl):
        if isinstance(acl, str):
            return self.has_acl(acl)

        return any(self.has_acl(a) for a in acl)

    def has_all(self, acl):
        if isinstance(acl, str):
            return self.has_acl(acl)

        return all(self.has_acl(a) for a in acl)

    def get(self, acl):
        return self.acl_map.get(acl)

    USERACL_MEMBERS = frozenset(a.value for a in
                                UserACLValues.__members__.values())

    def _add_nocommit(self, acl, setter=None, reason=None, time_=None):
        if acl in self.acl_map:
            return (False, ACLExistsError(acl))

        if acl not in self.USERACL_MEMBERS:
            return (False, ACLValueError(acl))

        self.acl_map[acl] = ACL(setter, reason, time_)
        return (True, None)

    def add(self, acl, setter=None, reason=None):
        if not isinstance(acl, str):
            for a in acl:
                self.add(a, setter, reason)

            return

        ret, code = self._add_nocommit(acl, setter, reason)
        if not ret:
            raise code

        asyncio.async(self.server.proto_store.create_user_acl(self.user, acl,
                                                              reason))

    def delete(self, acl):
        if not isinstance(acl, str):
            for a in acl:
                self.delete(a)

            return

        if acl not in self.acl_map:
            raise ACLDoesNotExistError('ACL does not exist')

        del self.acl_map[acl]

        asyncio.async(self.server.proto_store.del_user_acl(acl, self.user))


class GroupACLSet:
    __slots__ = ['server', 'group', 'acl_map']

    def __init__(self, server, group, acl_data=None):
        self.server = server
        self.group = group

        # XXX this is a hack and will change someday
        # (dict of a dict is no way to live)
        self.acl_map = defaultdict(dict)

        if not acl_data:
            return

        for acl in acl_data:
            self._add_nocommit(acl['target'], acl['acl'], acl['setter'],
                               acl['reason'], acl['timestamp'])

    def __iter__(self):
        for user, acl_ in self.acl_map.items():
            for acl in acl_:
                yield (user, acl)

    def has_acl(self, user, acl):
        user = getattr(user, 'name', user)
        return acl in self.acl_map[user]

    def has_any(self, user, acl):
        if isinstance(acl, str):
            return self.has_acl(user, acl)

        return any(self.has_acl(user, a) for a in acl)

    def has_all(self, user, acl):
        if isinstance(acl, str):
            return self.has_acl(user, acl)

        return all(self.has_acl(user, a) for a in acl)

    def get(self, user, acl):
        user = getattr(user, 'name', user)
        return self.acl_map.get(user)

    GROUPACL_MEMBERS = frozenset(a.value for a in
                                 GroupACLValues.__members__.values())

    def _add_nocommit(self, user, acl, setter=None, reason=None, time_=None):
        if acl in self.acl_map[user]:
            pass

        if acl not in self.GROUPACL_MEMBERS:
            if acl.replace('grant:', '') not in self.GROUPACL_MEMBERS:
                return

        self.acl_map[user][acl] = ACL(setter, reason, time_)

    def add(self, user, acl, setter=None, reason=None):
        user = getattr(user, 'name', user)
        if not isinstance(acl, str):
            for a in acl:
                self.add(user, a, setter, reason)

            return

        if acl in self.acl_map[user]:
            raise ACLExistsError(acl)

        if acl not in self.GROUPACL_MEMBERS:
            if acl.replace('grant:', '') not in self.GROUPACL_MEMBERS:
                # Allow special grant: ACL's
                raise ACLValueError(acl)

        self._add_nocommit(user, acl, setter, reason)

        asyncio.async(self.server.proto_store.create_group_acl(self.group,
                      user, acl, setter, reason))

    def delete(self, user, acl):
        user = getattr(user, 'name', user)
        if not isinstance(acl, str):
            for a in acl:
                self.delete(user, a)

            return

        if acl not in self.acl_map[user]:
            raise ACLDoesNotExistError('ACL does not exist')

        del self.acl_map[user][acl]

        asyncio.async(self.server.proto_store.del_group_acl(self.group, user,
                      acl))

    def delete_all(self, user):
        self.acl_map.pop(user, None)
