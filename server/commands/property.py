# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio

from server.command import Command, register
from server.property import UserPropertyValues, GroupPropertyValues


class PropertySet(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        if 'property' not in line.kval:
            server.error(user, line.command, 'No property specified', False,
                         {'target': [line.target]})
            return

        property = line.kval['property']
        value = line.kval.get('value')

        if len(property) != len(value):
            server.error(user, line.command, 'property-value length mismatch',
                         False,
                         {'target': [line.target], 'property': property})
            return

        target = server.get_any_target(line.target)
        if not target:
            server.error(user, line.command, 'Invalid target', False,
                         {'target': [line.target], 'property': property})
            return

        if target.name[0] == '#':
            # Must have the correct ACL
            acl_check = ('grant', 'grant:*', 'grant:property')
            if not target.acl.has_acl_any(acl_check):
                server.error(user, line.command, 'No permission', False,
                             {'target': [line.target], 'property': property})
                return

        try:
            target.property.set(property, value, user.name)
        except PropertyError as e:
            error = 'Error setting property: {}'.format(str(e))
            server.error(user, line.command, error, False,
                         {'target': [line.target], 'property': property})
            return

        if target.proto or target[0] == '#':
            target.send(user, line.command, line.kval)

        user.send(user, line.command, line.kval)


class PropertyDel(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        if 'property' not in line.kval:
            server.error(user, line.command, 'No property specified', False,
                         {'target': [line.target]})
            return

        property = line.kval['property']
        value = line.kval.get('value')

        if len(property) != len(value):
            server.error(user, line.command, 'Property-value length mismatch',
                         False,
                         {'target': [line.target], 'property': property})
            return

        target = server.get_any_target(line.target)
        if not target:
            server.error(user, line.command, 'Invalid target', False,
                         {'target': [line.target], 'property': property})
            return

        if target.name[0] == '#':
            # Must have the correct ACL
            acl_check = ('grant', 'grant:*', 'grant:property')
            if not target.acl.has_acl_any(acl_check):
                server.error(user, line.command, 'No permission', False,
                             {'target': [line.target], 'property': property})
                return

        try:
            target.property.delete(property, value, user.name)
        except PropertyError as e:
            error = 'Error revoking property: {}'.format(str(e))
            server.error(user, line.command, error, False,
                         {'target': [line.target], 'property': property})
            return

        if target.proto or target[0] == '#':
            target.send(user, line.command, line.kval)

        user.send(user, line.command, line.kval)

class PropertyList(ACLBase, Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        if 'property' not in line.kval:
            server.error(user, line.command, 'No property specified', False,
                         {'target': [line.target]})
            return

        target = server.get_any_target(line.target)
        if not target:
            server.error(user, line.command, 'Invalid target', False,
                         {'target': [line.target], 'property': property})
            return

        if target.name[0] == '#':
            # Verify they're in the group
            if not (user in group.members or 
                    user.acl.has_acl('group:auspex')):
                server.error(user, line.command, 'No permission', False,
                             {'target': [line.target], 'property': property})
                return

            # TODO more checks
        else:
            if not (target == user or user.acl.has_acl('user:auspex')):
                server.error(user, line.command, 'No permission', False,
                             {'target': [line.target], 'property': property})
                return

        # Get all properties
        property = []
        value = []
        timestamp = []
        setter = []
        for prop, val in target.property:
            property.append(prop)
            value.append(val.value)
            timestamp.append(val.time)
            setter.append(val.setter)

        kwds = {
            'property': property,
            'value': value,
            'timestamp': timestamp,
            'setter': setter,
        }

        user.send_multipart(server, user, line.command, ('property', 'value'),
                            kwds)


register.update({
    'property-set': PropertySet(),
    'property-del': PropertyDel(),
    'property-list': PropertyList()
})
