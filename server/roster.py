# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio


class RosterEntryUser:
    __slots__ = ['target', 'alias', 'group_tag', 'blocked']

    def __init__(self, target, alias=None, group_tag=None, blocked=False):
        self.target = target
        self.roster = roster

        if alias is None:
            alias = target.name.lower()

        self.alias = alias
        self.group_tag = group_tag
        self.blocked = bool(blocked)


class RosterEntryGroup:
    __slots__ = ['target', 'alias', 'group_tag']

    def __init__(self, target, alias=None, group_tag=None):
        self.target = target

        if alias is None:
            alias = target.name.lower()

        self.alias = alias
        self.group_tag = group_tag


class Roster:
    def __init__(self, server, user, entries=None):
        self.server = server
        self.proto_store = server.proto_store
        self.user = user.lower()
        self.roster_map = dict()

    def _add_nocommit(self, user, target, alias=None, group_tag=None,
                      blocked=False):
        if not hasattr(target, 'name'):
            target = (yield from server.get_any_target(target))

        if not target:
            return (False, TargetDoesNotExistError(target))

        user = getattr(user, 'name', user)

        tname = target.name.lower()

        if tname[0] == '#':
            inst = RosterEntryGroup
            args = (user, target, user, self, alias, group_tag)
        else:
            inst = RosterEntryUser
            args = (user, target, self, alias, group_tag, blocked)

        if target in self.roster_map:
            return (False, TargetExistsError())

        self.roster_map[tname] = inst(*args)
        return (True, None)

    def add(self, target, alias=None, group_tag=None):
        ret, exc = self._add_nocommit(target, alias, group_tag)
        if not ret:
            raise exc

        if target.name[0] == '#':
            function = self.proto_store.create_roster_group
        else:
            function = self.proto_store.create_roster_user

        target = getattr(target, 'name', target).lower()

        asyncio.async(function(user, target, alias, group_tag))

    def set(self, target, **kwargs):
        if not hasattr(target, 'name'):
            target = (yield from server.get_any_target(target))

        if not target:
            raise TargetDoesNotExistError()

        tname = target.name.lower()

        if tname not in self.roster_map:
            raise RosterDoesNotExistError()

        roster = self.roster_map[tname]

        try:
            for k, v in kwargs.items():
                setattr(roster, k, v)
        except AttributeError as e:
            raise RosterAttributeError from e

        asyncio.async(function(user, tname, **kwargs))

    def delete(self, target):
        target = getattr(target, 'name', target).lower()

        if target not in self.roster_map:
            raise RosterDoesNotExistError(target)

        function = (self.proto_store.del_roster_group if target[0] == '#'
                    else self.proto_store.del_roster_group)

        del self.roster_map[target]

        asyncio.async(function(user, target))

    def get(self, target):
        target = getattr(target, 'name', target).lower()

        if target not in self.roster_map:
            RosterDoesNotExistError(target)

        return self.roster_map[target]

    def __iter__(self):
        return self.roster_map.items()
