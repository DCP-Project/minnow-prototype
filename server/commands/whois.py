# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio

from server.command import Command, register
import server.acl as acl
import server.property as property


class Whois(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        target = line.target
        if target == '*' or target.startswith(('=', '#')):
            server.error(user, line.command, 'No valid target', False)
            return

        t_user = (yield from server.get_any_target(target))

        kval = {
            'handle': [t_user.name],
            'gecos': [t_user.gecos],
        }

        if len(t_user.sessions):
            kval['online'] = ['*']

        if user.acl.has_acl('user:auspex'):
            ip = []
            host = []
            for p in user.sessions:
                ip.append(p.peername[0])
                host.append(p.host)

            kval.update({
                'acl': sorted(user.acl),
                'ip': ip,
                'host': host,
            })

        if t_user.groups:
            group_prop = 'private'
            user_acl = 'user:auspex'
            kval['groups'] = [group for group in user.groups if not
                              (group_prop in group.property and not user_acl in
                               user.acl)]

        # FIXME - if WHOIS info is too big, split it up

        proto.send(server, user, 'whois', kval)


register['whois'] = Whois()
