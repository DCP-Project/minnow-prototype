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


class RosterList:
    def __init__(self, server, user):
