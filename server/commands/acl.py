# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio

from server.command import Command, register


class ACLBase:
    @asyncio.coroutine
    @staticmethod
    def has_grant_group(server, user, gtarget, acl):
        if user not in gtarget.users:
            return (False, 'Must be in group to alter ACL\'s in it')

        check_grant = ['grant:*']
        check_grant.extend('grant:' + a for a in acl)
        if gtarget.acl.has_any(check_grant):
            return (True, None)
        else:
            if not gtarget.acl.has_acl('group:grant'):
                return (False, 'No permission to alter ACL')

        return (True, None)

    @asyncio.coroutine
    @staticmethod
    def has_grant_user(server, user, utarget, acl):
        check_grant = ['user:grant']
        check_grant.extend(acl)
        if not gtarget.acl.has_acl_all(check_grant):
            return (False, 'No permission to alter ACL')

        return (True, None)

    @asyncio.coroutine
    @staticmethod
    def has_grant(server, user, gtarget, utarget, acl):
        target = getattr(target, 'name', target)

        if isinstance(acl, str):
            acl = (acl,)

        if target[0] == '#':
            ret = (yield from ACLBase.has_grant_group(server, user, gtarget,
                                                      acl))
        else:
            ret = (yield from ACLBase.has_grant_user(server, user, utarget,
                                                     acl))

        return ret

    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        if 'acl' not in line.kval or not line.kval['acl']:
            server.error(user, line.command, 'No ACL', False,
                         {'target': [target]})
            return (None, None)

        # Obtain target info
        line.kval['acl'] = acl = [a.lower() for a in line.kval['acl']]
        line.target = target = line.target.lower()
        if target == '*':
            server.error(user, line.command, 'No valid target', False,
                         {'acl': acl})
            return (None, None)
        elif target[0] == '#':
            if acl not in GroupACLValues:
                server.error(user, line.command, 'Invalid ACL', False,
                             {'target': [target], 'acl': acl})
                return (None, None)

            gtarget = (yield from server.get_any_target(target))
            utarget = line.kval.get('user')

            if not utarget:
                server.error(user, line.command, 'No valid user for target',
                             False, {'target': [target], 'acl': acl})
                return (None, None)

            utarget = (yield from server.get_any_target(utarget.lower()))
        elif target[0] == '=':
            server.error(user, line.command, 'ACL\'s can\'t be set on '
                         'servers yet', False,
                         {'target': [target], 'acl': acl})
            return (None, None)
        else:
            gtarget = None
            utarget = (yield from server.get_any_target(target))

        return (gtarget, utarget)


class ACLSet(ACLBase, Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        gtarget, utarget = super().registered(server, user, line)
        if (gtarget, utarget) == (None, None):
            return

        acl = line.kval['acl']

        if gtarget:
            kwds = {'target': [gtarget.name], 'user': [utarget.name]}
        else:
            kwds = {'target': [utarget.name]}

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
        except ACLError as e:
            error = 'Error adding ACL: {}'.format(str(e))
            server.error(user, line.command, error, False, kwds)
            return

        # Report to the target if they're online
        if gtarget:
            gtarget.send(server, user, line.command, kwds)
        elif utarget.proto:
            utarget.send(server, user, line.command, kwds)

        user.send(server, user, line.command, kwds)

    @asyncio.coroutine
    def ipc(self, server, proto, line):
        gtarget, utarget = super().registered(server, proto, proto, line)
        if (gtarget, utarget) == (None, None):
            return

        acl = line.kval['acl']

        if gtarget:
            kwds = {'target': [gtarget.name], 'user': [utarget.name]}
        else:
            kwds = {'target': [utarget.name]}

        reason = line.kval.get('reason')

        # Bam
        try:
            if gtarget:
                gtarget.acl.add(utarget, acl, proto, reason)
            else:
                utarget.acl.add(acl, proto, reason)
        except ACLError as e:
            error = 'Error adding ACL: {}'.format(str(e))
            server.error(user, line.command, error, False, kwds)
            return

        # Report to the target if they're online
        if gtarget:
            gtarget.send(server, proto, line.command, kwds)
        elif utarget.proto:
            utarget.send(server, proto, line.command, kwds)

        proto.send(server, None, line.commands, kwds)        

class ACLDel(ACLBase, Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        gtarget, utarget = super().registered(server, user, line)
        if (gtarget, utarget) == (None, None):
            return

        acl = line.kval['acl']

        if gtarget:
            kwds = {'target': [gtarget.name], 'user': [utarget.name]}
        else:
            kwds = {'target': [utarget.name]}

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
        except ACLError as e:
            error = 'Error deleting ACL: {}'.format(str(e))
            server.error(user, line.command, error, False, kwds)
            return

        # Report to the target if they're online
        if gtarget:
            gtarget.send(server, user, line.command, kwds)
        elif utarget.proto:
            utarget.send(server, user, line.command, kwds)

        user.send(server, user, line.command, kwds)

    @asyncio.coroutine
    def ipc(self, server, proto, line):
        gtarget, utarget = super().registered(server, proto, line)
        if (gtarget, utarget) == (None, None):
            return

        acl = line.kval['acl']

        if gtarget:
            kwds = {'target': [gtarget.name], 'user': [utarget.name]}
        else:
            kwds = {'target': [utarget.name]}

        reason = line.kval.get('reason')
        if reason:
            kwds['reason'] = [reason]

        # Bam
        try:
            if gtarget:
                gtarget.acl.delete(utarget, acl)
            else:
                utarget.acl.delete(acl)
        except ACLError as e:
            error = 'Error deleting ACL: {}'.format(str(e))
            server.error(user, line.command, error, False, kwds)
            return

        # Report to the target if they're online
        if gtarget:
            gtarget.send(server, proto, line.command, kwds)
        elif utarget.proto:
            utarget.send(server, proto, line.command, kwds)

        proto.send(server, None, line.command, kwds)


class ACLList(ACLBase, Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        gtarget, utarget = super().registered(server, user, line)
        if (gtarget, utarget) == (None, None):
            return

        acl = line.kval['acl']

        if gtarget:
            kwds = {'target': [gtarget.name], 'user': [utarget.name]}
        else:
            kwds = {'target': [utarget.name]}

        reason = line.kval.get('reason')
        if reason:
            kwds['reason'] = [reason]

        if gtarget:
            target = gtarget
        else:
            # ACL's should only be viewable by those with grant priv for users
            # TODO is this correct?
            ret, msg = (yield from self.has_grant(server, user, gtarget,
                                                  utarget, acl))
            if not ret:
                server.error(user, line.command, msg, False, kwds)
                return

            target = utarget

        entry = []
        timestamp = []
        setter = []
        for acl, val in target.acl:
            entry.append(acl)
            timestamp.append(val.time)
            setter.append(val.setter)

        kwds.update({
            'acl': entry,
            'timestamp': time,
            'setter': setter,
        })
        user.send_multipart(server, user, line.command,
                            ('acl', 'timestamp', 'setter'), kwds)

    @asyncio.coroutine
    def ipc(self, server, proto, line):
        gtarget, utarget = super().registered(server, proto, line)
        if (gtarget, utarget) == (None, None):
            return

        acl = line.kval['acl']

        if gtarget:
            kwds = {'target': [gtarget.name], 'user': [utarget.name]}
        else:
            kwds = {'target': [utarget.name]}

        reason = line.kval.get('reason')
        if reason:
            kwds['reason'] = [reason]

        if gtarget:
            target = gtarget
        else:
            # ACL's should only be viewable by those with grant priv for users
            # TODO is this correct?
            ret, msg = (yield from self.has_grant(server, user, gtarget,
                                                  utarget, acl))
            if not ret:
                server.error(user, line.command, msg, False, kwds)
                return

            target = utarget

        entry = []
        timestamp = []
        setter = []
        for acl, val in target.acl:
            entry.append(acl)
            timestamp.append(val.time)
            setter.append(val.setter)

        kwds.update({
            'acl': entry,
            'timestamp': time,
            'setter': setter,
        })
        proto.send_multipart(server, None, line.command,
                             ('acl', 'timestamp', 'setter'), kwds)


register.update({
    'acl-set': ACLSet(),
    'acl-del': ACLDel(),
    'acl-list': ACLList()
})
