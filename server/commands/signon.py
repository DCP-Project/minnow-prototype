import asyncio
import crypt
import hmac

import server.parser as parser

from server.command import Command, register


class Signon(Command):
    @asyncio.coroutine
    def unregistered(self, server, proto, line):
        if server.servpass:
            rservpass = line.kval.get('servpass', [None])[0]
            if rservpass != server.servpass:
                server.error(proto, line.command, 'Bad server password')
                return

        name = line.kval.get('handle', [None])[0]
        if name is None:
            server.error(proto, line.command, 'No handle')
            return

        if len(name) > parser.MAXTARGET:
            server.error(proto, line.command, 'Handle is too long', True,
                         {'handle': [name]})
            return

        # Retrieve the user info
        user = server.get_any_target(name)
        if user is None:
            server.error(proto, line.command, 'You are not registered with '
                         'the server', False, {'handle': [name]})
            return
        elif user.proto:
            # TODO - burst all state to the user
            server.error(proto, line.command, 'No multiple users at the '
                         'moment', True, {'handle': [name]})
            return

        if 'password' not in line.kval:
            server.error(proto, line.command, 'No password given')
            return

        password = line.kval.get('password')[0]
        h = crypt.crypt(line.kval.get(password, uinfo['password']))
        if not hmac.compare_digest(h, uinfo['password']):
            server.error(proto, line.command, 'Invalid password')
            return

        options = line.kval.get('options', [])

        yield from server.user_enter(proto, user, options)

register['signon'] = Signon()
