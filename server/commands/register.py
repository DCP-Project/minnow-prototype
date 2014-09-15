# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio

import server.acl as acl

from server.command import Command, register
from settings import *


class Register(Command):
    @asyncio.coroutine
    def unregistered(self, server, proto, line):
        if server.servpass:
            rservpass = line.kval.get('servpass', [None])[0]
            if rservpass != server.servpass:
                server.error(proto, line.command, 'Bad server password')
                return

        if not allow_register:
            server.error(proto, line.command, 'Direct registrations are not '
                         'permitted on this server')
            return

        name = line.kval.get('handle', [None])[0]
        gecos = line.kval.get('gecos', [name])[0]
        password = line.kval.get('password', [None])[0]

        user = (yield from server.user_register(proto, name, gecos, password,
                                                line.command))
        if user is None:
            return

        kval = {
            'handle': [name],
            'gecos': [gecos],
            'message': ['Registration successful, beginning signon'],
        }
        proto.send(server, None, line.command, kval)

        options = line.kval.get('options', [])

        yield from server.user_enter(proto, user, options)


class FRegister(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        if acl.UserACLValues.user_register not in user.acl:
            server.error(user, line.command, 'No permission', False)
            return

        name = line.kval.get('handle', [None])[0]
        gecos = line.kval.get('gecos', [name])[0]
        password = line.kval.get('password', [None])[0]

        ret = (yield from server.user_register(proto, name, gecos, password,
                                               line.command))
        if not ret:
            return

        kval = {
            'handle': [name],
            'gecos': [gecos],
            'message': ['Registration successful'],
        }
        proto.send(server, None, line.command, kval)


register.update({
    'register': Register(),
    'fregister': FRegister(),
})
