# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio


class RosterEntryUser:
    __slots__ = ['user', 'roster', 'alias', 'group_tag', 'blocked']

    def __init__(self, user, roster, alias=None, group_tag=None,
                 blocked=False):
        self.user = user
        self.roster = roster

        if alias is None:
            alias = user.name.lower()

        self.group_tag = group_tag
        self.blocked = bool(blocked)


class RosterEntryGroup:
    __slots__ = ['group', 'roster', 'alias', 'group_tag', 'blocked']

    def __init__(self, group, roster, alias=None, group_tag=None):
        self.group = group
        self.roster = roster

        if alias is None:
            alias = group.name.lower()

        self.group_tag = group_tag


class Roster:
    def __init__(self, server, user, member_user=None, member_group=None):
        self.server = server
        self.user = user

        self.entry_user = dict()
        self.entry_group = dict()

    def _add_nocommit(self, target, alias=None, group_tag=None,
                      blocked=False):
        orig_target = target
        target = target.lower()

        if target[0] == '#':
            inst = RosterEntryGroup
            d = self.entry_group
            args = (orig_target, self, alias, group_tag)
        else:
            inst = RosterEntryUser
            d = self.entry_user
            args = (orig_target, self, alias, group_tag, blocked)

        d[target] = inst(*args)

    def add(self, target, alias=None, group_tag=None):
        self._add_nocommit(target, alias, group_tag)

    def delete(self, target):
        target = target.lower()
        try:
            if target[0] == '#':
                del self.entry_group[target]
            else:
                del self.entry_user[target]
        except KeyError as e:
            raise RosterDoesNotExistError(target) from e
