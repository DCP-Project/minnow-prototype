from command import Command, register
import acl
import config
import asyncio

class Whois(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        target = line.target
        if target == '*' or target.startswith(('=', '#')):
            server.error(user, line.command, 'No valid target', False)
            return

        if target not in server.online_users:
            server.error(user, line.command, 'No such user', False)
            return

        t_user = server.get_any_target(target)

        kval = {
            'handle' : [t_user.name],
            'gecos' : [t_user.gecos],
        }

        if user.acl.has_acl(acl.UserACLValues.user_auspex):
            ip = []
            host = []
            for p in user.sessions:
                ip.append(p.peername[0])
                host.append(p.host)

            kval.update({
                'acl' : sorted(user.acl),
                'ip' : ip,
                'host' : host,
            })

        if t_user.groups:
            group_prop = config.GroupConfigValues.private
            user_acl = config.UserConfigValues.user_auspex
            kval['groups'] = [group for group in user.groups if not
                              (group_prop in group.config and not user_acl in
                               user.acl)]

        # FIXME - if WHOIS info is too big, split it up

        proto.send(server, user, 'whois', kval)


register['whois'] = Whois()
