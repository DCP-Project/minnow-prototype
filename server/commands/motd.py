from server.command import Command, register

import asyncio

class MOTD(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        server.user_MOTD(user)


register['motd'] = MOTD()
