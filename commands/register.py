import asyncio

import acl

from command import Command, register
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
            server.error(proto, line.command, 'Direct registrations are not ' \
                       'permitted on this server')
            return

        name = line.kval.get('handle', [None])[0]
        gecos = line.kval.get('gecos', [name])[0]
        password = line.kval.get('password', [None])[0]

        if not server.user_register(proto, name, gecos, password):
            return

        kval = {
            'handle' : [name],
            'gecos' : [gecos],
            'message' : ['Registration successful, beginning signon'],
        }
        proto.send(self, None, line.command, kval)

        options = line.kval.get('options', [])

        yield from server.user_enter(proto, name, gecos, None, None, options)


class FRegister(Command):
    @asyncio.coroutine
    def registered(self, server, user, line):
        if acl.UserACLValues.user_register not in user.acl:
            server.error(user, line.command, 'No permission', False)
            return

        name = line.kval.get('handle', [None])[0]
        gecos = line.kval.get('gecos', [name])[0]
        password = line.kval.get('password', [None])[0]

        if not server.user_register(user, name, gecos, password):
            return

        kval = {
            'handle' : [name],
            'gecos' : [gecos],
            'message' : ['Registration successful'],
        }
        proto.send(self, None, line.command, kval)


register.update({
    'register' : Register(),
    'fregister' : FRegister(),
})
