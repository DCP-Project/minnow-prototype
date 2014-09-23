# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio
import enum
from time import time

from server.storageset import StorageSet, StorageItem
from server.storage.abstractor import ACLAbstractor

ACLAbstractor = ACLAbstractor.__subclasses__()[0]


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
    ban_banned = 'prohibit:ban'
    ban_usermessage = 'prohibit:usermessage'


class GroupACLValues(enum.Enum):
    # Allowance ACL's
    kick = 'kick'
    ban = 'ban'
    mute = 'mute'
    voice = 'voice'
    invex = 'invex'

    topic = 'topic'
    property = 'property'
    clear = 'clear'

    # IRC compatibility gunk
    owner = 'owner'  # Implies everything (see owner property)
    admin = 'admin'  # Also implies everything
    op = 'op'  # Everything except clear
    halfop = 'halfop'  # Everything except property, clear, and grant

    grant = 'grant'

    # Prohibition ACL's
    prohibit_banned = 'prohibit:ban'
    prohibit_mute = 'prohibit:mute'


class ACL(StorageItem):
    __slots__ = ['setter', 'reason', 'time']

    def __init__(self, setter=None, reason=None, time_=None):
        if time_ is None:
            time_ = round(time())

        super().__init__(self, setter, reason, time=time_)


class ACLSet(TargetStorageSet):

    eager = True
    check_db_fail = False  # XXX

    def __init__(self, server, target):
        self.server = server
        super().__init__(roster_factory, RosterAbstractor(server.proto_store),
                         target)

    def _get_key(self, key):
        return key.lower()

    @asyncio.coroutine
    def _check_setter(self, acl, setter):
        if setter is not None:
            if not hasattr(setter, 'name'):
                setter = self.server.get_any_target(setter)

            if not (yield from setter.acl.has('grant')):
                raise CommandACLError('grant')

            if not (yield from setter.acl.has(acl)):
                raise CommandACLError(acl)

    @asyncio.coroutine
    def add(self, acl, setter=None, reason=None, time=None):
        yield from self._check_setter(acl, setter)
        yield from super().add(acl, setter, reason, time)

    @asyncio.coroutine
    def _add_db(self, acl, setter=None, reason=None, time=None):
        yield from super()._add_db(acl, setter, reason)

    @asyncio.coroutine
    def set(self, acl, setter=None, reason=None, time=None):
        yield from self._check_setter(acl, setter)
        yield from super().set(acl, setter, reason, time)

    @asyncio.coroutine
    def _set_db(self, acl, setter=None, reason=None, time=None):
        yield from super()._set_db(acl, setter, reason, time)

    @asyncio.coroutine
    def delete(self, acl, setter=None):
        yield from self._check_setter(acl, setter)
        super().delete(acl)
