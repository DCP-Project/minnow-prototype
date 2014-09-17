# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio


class RosterEntryBase:
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
    def __init__(self, server, user, member_user=None, member_group=None):
        self.server = server
        self.proto_store = server.proto_store

        user = getattr(user, 'name', user).lower()

        self.user = user

        self.roster_map = dict()

    def _add_nocommit(self, user, target, alias=None, group_tag=None,
                      blocked=False):
        user = getattr(user, 'name', user)

        if not hasattr(target, 'name'):
            target = server.get_any_target(target)

        if not target:
            # FIXME lazy
            return (False, TargetDoesNotExistError(target))

        tname = target.name.lower()

        if tname[0] == '#':
            inst = RosterEntryGroup
            args = (user, target, user, self, alias, group_tag)
        else:
            inst = RosterEntryUser
            args = (user, target, self, alias, group_tag, blocked)

        if user in d:
            # FIXME needs a proper error
            return (False, UserExistsError())

        self.roster_map[tname] = inst(*args)
        return True

    def add(self, target, alias=None, group_tag=None):
        ret, exc = self._add_nocommit(target, alias, group_tag)
        if not ret:
            raise exc

        if target.name[0] == '#':
            function = self.proto_store.create_roster_group
            asyncio.async(function(user, target.name.lower(), alias,
                                   group_tag))
        else:
            function = self.proto_store.create_roster_user

        asyncio.async(function(user, target.name.lower(), alias, group_tag))

    def set(self, target, **kwargs):
        target = server.get_any_target(target)
        if not target:
            # FIXME lazy
            raise TargetDoesNotExistError()

        tname = target.name.lower()

        if tname not in self.roster_map:
            raise RosterDoesNotExistError()

        try:
            roster = d[tname]
            for k, v in kwargs.items():
                setattr(roster, k, v)
        except AttributeError as e:
            raise RosterAttributeError from e

        asyncio.async(function(user, tname, **kwargs))

    def delete(self, target):
        target = getattr(target, 'name', target).lower()
        try:
            function = (self.proto_store.del_roster_group if target[0] == '#'
                        else self.proto_store.del_roster_group)
            del self.entry_user[target]
        except KeyError as e:
            raise RosterDoesNotExistError(target) from e

        asyncio.async(function(user, target))
