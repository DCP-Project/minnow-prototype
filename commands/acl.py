from command import Command, register
from acl import UserACLValues, GroupACLValues

import asyncio

class ACLBase:
    @asyncio.coroutine
    def has_grant_group(self, server, user, gtarget, acl):
        if user not in gtarget.users:
            return (False, 'Must be in group to alter ACL\'s in it')

        if gtarget.acl.has_any(('grant', 'grant:*', 'grant:' + acl)):
            return (True, None)
        else:
            if not gtarget.acl.has_acl('group:grant'):
                return (False, 'No permission to alter ACL')

        return (True, None)

    @asyncio.coroutine
    def has_grant_user(self, server, user, utarget, acl):
        if not gtarget.acl.has_acl_all(('user:grant', acl)):
            return (False, 'No permission to alter ACL')

        return (True, None)

    @asyncio.coroutine
    def has_grant(self, server, user, gtarget, utarget, acl):
        target = getattr(target, 'name', target)

        if target[0] == '#':
            ret = (yield from self.has_grant_group(server, user, gtarget,
                                                   acl))
        else:
            ret = (yield from self.has_grant_user(server, user, utarget, acl))
        
        return ret

    def registered(self, server, user, proto, line):
        if acl not in line.kval or not line.kval['acl']:
            server.error(user, line.command, 'No ACL', False,
                         {'target' : [target]})
            return (None, None)

        # Obtain target info
        line.kval['acl'] = acl = line.kval['acl'].lower()
        line.target = target = line.target.lower()
        if target == '*':
            server.error(user, line.command, 'No valid target', False,
                         {acl : [acl]})
            return (None, None)
        elif target[0] == '#':
            if acl not in GroupACLValues:
                server.error(user, line.command, 'Invalid ACL', False,
                             {'target' : [target], 'acl' : [acl]})
                return (None, None)

            gtarget = (yield from server.get_any_target(target))
            utarget = line.kval.get('user')

            if not utarget:
                server.error(user, line.command, 'No valid user for target',
                             False, {'target' : [target], 'acl' : [acl]})
                return (None, None)

            utarget = (yield from server.get_any_target(utarget.lower()))
        elif target[0] == '=':
            server.error(user, line.command,
                         'ACL\'s can\'t be set on servers yet',
                         False, {'target' : [target], 'acl' : [acl]})
            return (None, None)
        else:
            if acl not in UserACLValues:
                server.error(user, line.command, 'Invalid ACL', False,
                             {'target' : [target], 'acl' : [acl]})
                return (None, None)

            gtarget = None
            utarget = (yield from server.get_any_target(target))

        return (gtarget, utarget)

class ACLSet(ACLBase, Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        gtarget, utarget = super().registered(server, user, line)
        if (gtarget, utarget) == (None, None):
            return

        if gtarget:
            kwds = {'target' : [gtarget.name], 'user' : [utarget.name]}
        else:
            kwds = {'target' : [utarget.name]}

        reason = line.kval.get('reason')
        if reason:
            kwds['reason'] = [reason]

        ret, msg = (yield from self.has_grant(server, user, gtarget, utarget,
                                              acl))
        if not ret:
            server.error(user, line.command, msg, False, kwds)
            return

        # Bam
        try:
            if gtarget:
                gtarget.acl.add(utarget, acl, user, reason)
            else:
                utarget.acl.add(acl, user, reason)
        except ACLExistsError as e:
            server.error(user, line.command, 'ACL exists', False, kwds)
            return

        # Report to the target if they're online
        if gtarget:
            gtarget.send(server, user, line.command, kwds)
        elif utarget.proto:
            utarget.send(server, user, line.command, kwds)


class ACLDel(Command, ACLBase):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        gtarget, utarget = super().registered(server, user, line)
        if (gtarget, utarget) == (None, None):
            return

        if gtarget:
            kwds = {'target' : [gtarget.name], 'user' : [utarget.name]}
        else:
            kwds = {'target' : [utarget.name]}

        reason = line.kval.get('reason')
        if reason:
            kwds['reason'] = [reason]

        ret, msg = (yield from self.has_grant(server, user, gtarget, utarget,
                                              acl))
        if not ret:
            server.error(user, line.command, msg, False, kwds)
            return

        # Bam
        try:
            if gtarget:
                gtarget.acl.delete(utarget, acl)
            else:
                utarget.acl.delete(acl)
        except ACLDoesNotExistError as e:
            server.error(user, line.command, 'ACL does not exist', False, kwds)
            return

        # Report to the target if they're online
        if gtarget:
            gtarget.send(server, user, line.command, kwds)
        elif utarget.proto:
            utarget.send(server, user, line.command, kwds)

register.update({
    'acl-set' : ACLSet(),
    'acl-del' : ACLDel(),
})
