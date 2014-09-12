from command import Command, register
import asyncio

class Message(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        target = line.target
        if target == '*':
            server.error(user, line.command, 'No valid target', False)
            return

        # Lookup the target...
        if target.startswith(('=', '&')):
            server.error(user, line.command, 'Cannot message servers yet, sorry',
                       False, {'target' : [target]})
            return
        elif target.startswith('#'):
            if target not in server.groups:
                server.error(user, line.command, 'No such group', False,
                           {'target' : [target]})
                return

            target = server.groups[target]
        else:
            if target not in server.online_users:
                server.error(user, line.command, 'No such user', False,
                           {'target' : [target]})
                return

            target = server.online_users[target]

        # Get our message
        message = line.kval.get('body', [''])

        # Bam
        target.Message(user, message)


register['message'] = Message()
