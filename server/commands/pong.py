import asyncio

from server.command import Command, register

class Pong(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        user.timeout = False


register['pong'] = Pong()
