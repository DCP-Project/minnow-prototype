import asyncio

from server.command import Command, register


class Message(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        target = line.target
        if target == '*':
            server.error(user, line.command, 'No valid target', False)
            return

        # Lookup the target...
        if target.startswith(('=', '&')):
            server.error(user, line.command, 'Cannot message servers yet, '
                         'sorry', False, {'target': [target]})
            return

        target = server.get_online_target(target)

        # Get our message
        message = line.kval.get('body', [''])

        # Bam
        target.Message(user, message)


register['message'] = Message()
