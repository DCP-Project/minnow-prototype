# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio


class RosterEntryUser:
    __slots__ = ['target', 'alias', 'group_tag', 'pending', 'blocked']

    def __init__(self, target, alias=None, group_tag=None, pending=False,
                 blocked=False):
        self.target = target
        self.roster = roster

        if alias is None:
            alias = target.name.lower()

        self.alias = alias
        self.group_tag = group_tag
        self.pending = bool(pending)
        self.blocked = bool(blocked)


class RosterEntryGroup:
    __slots__ = ['target', 'alias', 'group_tag']

    def __init__(self, target, alias=None, group_tag=None):
        self.target = target

        if alias is None:
            alias = target.name.lower()

        self.alias = alias
        self.group_tag = group_tag


class RosterSet:
    def __init__(self, server, user, entries_u=[], entries_g=[]):
        self.server = server
        self.proto_store = server.proto_store
        self.user = user.lower()
        self.roster_map = dict()

        if entries_u:
            for entry in entries_u:
                self._add_nocommit(entry['name'], entry['alias'],
                                   entry['group_tag'], entry['pending'],
                                   entry['blocked'])

        if entries_g:
            for entry in entries_g:
                self._add_nocommit(entry['name'], entry['alias'],
                                   entry['group_tag'])

    def _add_nocommit(self, target, alias=None, group_tag=None,
                      pending=False, blocked=False):
        if not hasattr(target, 'name'):
            target = (yield from server.get_any_target(target))

        if not target:
            return (False, TargetDoesNotExistError(target))

        tname = target.name.lower()

        if tname[0] == '#':
            inst = RosterEntryGroup
            args = (target, alias, group_tag)
        else:
            inst = RosterEntryUser
            args = (target, alias, group_tag, pending, blocked)

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
