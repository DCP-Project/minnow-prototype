# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio

import server.parser as parser

from server.command import Command, register


class GroupEnter(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        target = line.target
        if target == '*':
            server.error(user, line.command, 'No valid target', False)
            return

        if not target.startswith('#'):
            server.error(user, line.command, 'Invalid group', False,
                         {'target': [target]})
            return

        if len(target) > parser.MAXTARGET:
            server.error(user, line.command, 'Group name too long', False,
                         {'target': [target]})
            return

        if target not in server.groups:
            logger.info('Creating group %s', target)
            server.groups[target] = Group(target)

        group = server.groups[target]
        if group in user.groups:
            assert user in group.users
            server.error(user, line.command, 'You are already entered', False,
                         {'target': [target]})
            return

        kval = {}
        reason = line.kval.get('reason')
        if reason is not None:
            kval['reason'] = [reason]

        group.member_add(user, reason)


class GroupExit(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        target = line.target
        if target == '*':
            server.error(user, line.command, 'No valid target', False)
            return

        if not target.startswith('#') or target not in server.groups:
            server.error(user, line.command, 'Invalid group', False,
                         {'target': [target]})
            return

        group = server.groups[target]
        if group not in user.groups:
            assert user not in group.users
            server.error(user, line.command, 'You are not in that group',
                         False, {'target': [target]})
            return

        kval = {}
        reason = line.kval.get('reason')
        if reason is not None:
            kval['reason'] = [reason]

        group.member_del(user, kval)
        group.send(self, user, 'group-exit', kval)

register.update({
    'group-enter': GroupEnter(),
    'group-exit':  GroupExit(),
})
