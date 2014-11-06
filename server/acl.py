# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio
import enum

from time import time
from collections import namedtuple


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


ACLGroupKey = namedtuple('ACLGroupKey', ('user', 'acl'))


class ACLUserList:
    def __init__(self):
        self.acl = dict()

    def grant(self, acl, setter=None, reason=None, time_=None):
        acl = UserACLValues(acl.casefold())
        self.acl[acl] = ACL(setter, reason, time_)

    def revoke(self, acl):
        self.acl.pop(UserACLValues(acl.casefold()))

    def check(self, acl):
        acl = UserACLValues(acl.casefold())
        return self.acl.get(acl, None)


class ACLGroupList:
    def __init__(self):
        self.acl = dict()

    def grant(self, acl, user, setter=None, reason=None, time_=None):
        key = ACLGroupKey(acl.casefold(), user.name.casefold())
        self.acl[key] = ACL(setter, reason, time_)

    def revoke(self, acl, user):
        key = ACLGroupKey(acl.casefold(), user.name.casefold())
        self.acl.pop(key)

    def check(self, acl, user):
        key = ACLGroupKey(acl.casefold(), user.name.casefold())
        return self.acl.get(key, None)
