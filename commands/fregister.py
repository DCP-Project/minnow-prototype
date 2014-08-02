from command import Command, register
import acl
import asyncio

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


register['fregister'] = FRegister()
