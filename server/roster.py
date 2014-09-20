# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio

from server import storageset
from server.storage.abstractor import RosterAbstractor

RosterAbstractor = RosterAbstractor.__subclasses__()[0]


class RosterEntryUser(storageset.StorageItem):

    __slots__ = ['target', 'alias', 'group_tag', 'pending', 'blocked']

    def __init__(self, target, alias=None, group_tag=None, pending=False,
                 blocked=False):
        if alias is None:
            alias = target.name.lower()

        pending = bool(pending)
        blocked = bool(blocked)

        super().__init__(**locals())


class RosterEntryGroup(storageset.StorageItem):

    __slots__ = ['target', 'alias', 'group_tag']

    def __init__(self, target, alias=None, group_tag=None):
        if alias is None:
            alias = target.name.lower()

        super().__init__(**locals())


def roster_factory(self, target, alias=None, group_tag=None, pending=False,
                   blocked=False):
    if target[0] == '#':
        return RosterEntryGroup(target, alias, group_tag)
    else:
        return RosterEntryUser(target, alias, group_tag, pending, blocked)


class RosterSet(StorageSet):

    eager = True
    check_db_fail = False  # XXX

    def __init__(self, server, user):
        self.server = server
        super().__init__(roster_factory, RosterAbstractor(server.proto_store))

    @asyncio.coroutine
    def add(self, target, alias=None, group_tag=None, pending=None):
        if not hasattr(target, 'name'):
            target = (yield from self.server.get_any_target(target))

        yield from super().add(target, alias, group_tag, pending)

    @asyncio.coroutine
    def _add_db(self, target, alias=None, group_tag=None, **kwargs):
        assert not bool(kwargs)
        yield from super()._add_db(target, alias, group_tag)

    @asyncio.coroutine
    def set(self, target, alias=None, group_tag=None, pending=None,
            blocked=None):
        if not hasattr(target, 'name'):
            target = (yield from self.server.get_any_target(target))

        yield from super().set(target, alias, group_tag, pending, blocked)

    @asyncio.coroutine
    def _set_db(self, target, alias=None, group_tag=None, pending=None,
                blocked=None, **kwargs):
        assert not bool(kwargs)
        yield from super()._set_db(target, alias, group_tag, pending, blocked)

    @asyncio.coroutine
    def delete(self, target):
        if not hasattr(target, 'name'):
            target = (yield from self.server.get_any_target(target))

        yield from super().delete(target)

    @asyncio.coroutine
    def _delete_db(self, target, **kwargs):
        assert not bool(kwargs)
        yield from super().delete(target)

    def _get_db(self, target):
        raise NotImplementedError()
