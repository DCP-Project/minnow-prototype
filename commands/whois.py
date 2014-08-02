from command import Command, register
import acl
import config
import asyncio

class Whois(Command):
    @asyncio.coroutine
    def registered(self, server, user, line):
        target = line.target
        if target == '*' or target.startswith(('=', '#')):
            server.error(user, line.command, 'No valid target', False)
            return

        if target not in server.users:
            server.error(user, line.command, 'No such user', False)
            return

        user = server.users[target]

        kval = {
            'handle' : [user.name],
            'gecos' : [user.gecos],
        }

        print(user.acl)
        if acl.UserACLValues.user_auspex in user.acl:
            ip = user.proto.peername[0]

            kval.update({
                'acl' : sorted(user.acl),
                'ip' : [ip],
                'host' : [user.proto.host],
            })

        if user.groups:
            group_prop = config.GroupConfigValues.private
            user_acl = config.UserConfigValues.user_auspex
            kval['groups'] = [group for group in user.groups if not
                              (group_prop in group.config and not user_acl in
                               user.acl)]

        # FIXME - if WHOIS info is too big, split it up

        user.send(self, user, 'whois', kval)


register['whois'] = Whois()
