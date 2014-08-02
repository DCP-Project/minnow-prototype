from command import Command, register
import parser
import asyncio

class group_enter(Command):
    @asyncio.coroutine
    def registered(self, server, user, line):
        target = line.target
        if target == '*':
            server.error(user, line.command, 'No valid target', False)
            return

        if not target.startswith('#'):
            server.error(user, line.command, 'Invalid group', False,
                       {'target' : [target]})
            return

        if len(target) > parser.MAXTARGET:
            server.error(user, line.command, 'Group name too long', False,
                       {'target' : [target]})
            return

        if target not in server.groups:
            logger.info('Creating group %s', target)
            server.groups[target] = Group(target)

        group = server.groups[target]
        if group in user.groups:
            assert user in group.users
            server.error(user, line.command, 'You are already entered', False,
                       {'target' : [target]})
            return

        group.member_add(user, line.kval.get('reason', [''])[0])


class group_exit(Command):
    @asyncio.coroutine
    def registered(self, server, user, line):
        target = line.target
        if target == '*':
            server.error(user, line.command, 'No valid target', False)
            return

        if not target.startswith('#') or target not in server.groups:
            server.error(user, line.command, 'Invalid group', False,
                       {'target' : [target]})
            return

        group = server.groups[target]
        if group not in user.groups:
            assert user not in group.users
            server.error(user, line.command, 'You are not in that group', False,
                       {'target' : [target]})
            return

        group.member_del(user, line.kval.get('reason', ['']))

register.update({
    'group-enter' : group_enter(),
    'group-exit' :  group_exit(),
})

