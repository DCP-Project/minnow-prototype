# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import enum
import time
import asyncio
import re
import inspect
import random
import functools
import crypt
import logging
import traceback

import server.command as command
import server.parser as parser

from server.acl import UserACLSet, GroupACLSet
from server.user import User
from server.group import Group
from server.storage.asyncstorage import AsyncStorage
from server.errors import *
from settings import *

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# This is subject to change
valid_handle = re.compile(r'^[^#!=&$,\?\*\[\]][^=$,\?\*\[\]]+$')


class DCPServer:
    def __init__(self, name, servpass=servpass):
        self.name = name
        self.servpass = servpass

        self.online_users = dict()
        self.groups = dict()

        self.proto_store = AsyncStorage(store_backend, store_backend_args)

        self.motd = None
        self.motd_load()

    def motd_load(self):
        try:
            with open('motd.txt', 'r') as f:
                self.motd = f.read()
        except Exception as e:
            logger.exception('Could not read MOTD')

    def error(self, dest, command_, reason, fatal=True, extargs=None,
              source=None):
        if hasattr(dest, 'proto'):
            proto = dest.proto
        elif hasattr(dest, 'error'):
            proto = dest
        else:
            raise Exception('No proto in dest {}!'.format(repr(dest)))

        if fatal:
            proto = getattr(dest, 'proto', dest)
            logger.debug('Fatal error encountered for client %r (%s: %s [%r])',
                         proto.peername, command_, reason, extargs)

        proto.error(command_, reason, fatal, extargs, source)

    def _call_func(self, proto, line):
        instance = command.register.get(line.command.lower(), None)
        if instance is None:
            self.error(proto, line.command, 'No such command', False)
            return

        # Determine which function to use
        if hasattr(proto, 'user'):
            # User found
            if proto.user is None:
                function = instance.unregistered
                args = (self, proto, line)
            else:
                function = instance.registered
                args = (self, proto.user, proto, line)
        elif hasattr(proto, 'remote'):
            # NOTE: not used yet
            function = instance.sts
            args = (self, proto.remote, proto, line)
        else:
            function = instance.ipc
            args = (self, proto, line)

        try:
            return (yield from function(*args))
        except CommandNotImplementedError as e:
            if proto:
                self.error(proto, line.command, str(e))

    def user_enter(self, proto, user, options):
        print(proto)
        proto.user = self.online_users[user.name.lower()] = user
        user.sessions.add(proto)

        user.options = options

        # Cancel the timeout
        proto.call_cancel('signon')

        kval = {
            'name': [self.name],
            'time': [str(round(time.time()))],
            'version': ['Minnow prototype server', 'v0.1-prealpha'],
            'options': [],
        }

        yield from proto.rdns
        if proto.host != proto.peername[0]:
            kval['host'] = [proto.host]

        user.send(self, user, 'signon', kval)

        # Send the MOTD
        self.user_motd(user, proto)

        # Ping timeout stuff
        user.timeout = False
        self.ping_timeout(proto)

    def user_exit(self, user, proto, reason=None):
        user.sessions.discard(proto)
        if not user.sessions:
            del self.online_users[user.name.lower()]

        kval = {
            'quit': ['*'],
        }

        if reason is not None:
            kval['reason'] = [reason]

        for group in list(user.groups):
            # Part them from all groups
            group.member_del(user)

            group.send(self, user, 'group-exit', kval)

    @asyncio.coroutine
    def user_register(self, proto, name, gecos, password, command):
        if name is None:
            self.error(proto, command, 'No handle', False)
            return False

        if valid_handle.match(name) is None:
            self.error(proto, command, 'Invalid handle', False,
                       {'handle': [name]})
            return False

        if len(name) > parser.MAXTARGET:
            self.error(proto, command, 'Handle is too long', False,
                       {'handle': [name]})
            return False

        f = yield from self.proto_store.get_user(name.lower())
        if f is not None:
            self.error(proto, command, 'Handle already registered', False,
                       {'handle': [name]})
            return False

        if len(gecos) > parser.MAXTARGET:
            self.error(proto, command, 'GECOS is too long', False,
                       {'gecos': [gecos]})
            return False

        if password is None or len(password) < 5:
            # Password is not sent back for security reasons
            self.error(proto, command, 'Bad password', False)
            return False

        password = crypt.crypt(password, crypt.mksalt())

        # Bang
        yield from self.proto_store.create_user(name.lower(), gecos, password)

        # Clear the user cache
        self.get_any_target.cache_clear()

        # Poop out a new user object
        return User(self, name, gecos)

    def user_motd(self, user, proto):
        if not self.motd:
            proto.send(self, user, 'motd', {})
            return

        kval = {
            'text': [self.motd],
        }
        proto.send_multipart(self, user, 'motd', ['text'], kval)

    def ping_timeout(self, proto):
        if proto.timeout:
            logger.debug('Connection %r timed out', proto.peername)
            self.error(proto, 'ping', 'Ping timeout')
            return

        t = str(round(time.time()))
        proto.send(self, proto, 'ping', {'time': [t]})

        user.timeout = True

        proto.call_ish('ping', 45, 60, self.ping_timeout, proto)

    def conn_timeout(self, proto):
        if proto.user:
            # They've signed on, no need
            proto.call_cancel('signon')
            return

        self.error(proto, '*', 'Connection timed out')

    def get_online_target(self, target):
        if target == '*':
            return

        target = target.lower()
        if target[0] == '#' and target in self.groups:
            return self.groups[target]
        elif target in self.online_users:
            return self.online_users[target]

    @asyncio.coroutine
    @functools.lru_cache(maxsize=max_cache)
    def get_any_target(self, target):
        """ Get a target in any state

        Note the target is offline if proto is None
        """

        target = target.lower()

        ret = self.get_online_target(target)
        if ret is not None:
            return ret

        if target.startswith('#'):
            g_data = (yield from self.proto_store.get_group(target))
            if g_data is None:
                return None

            acl_data = (yield from self.proto_store.get_group_acl(target))
            acl_set = GroupACLSet(self, target, acl_data)

            prop_data = (yield from self.proto_store.get_group_property(
                target))
            prop_set = GroupPropertySet(self, target, prop_data)

            return Group(self, target, g_data['topic'], acl_set,
                         prop_set, g_data['timestamp'])
        else:
            u_data = (yield from self.proto_store.get_user(target))
            if u_data is None:
                print("User not found", target)
                return None

            acl_data = (yield from self.proto_store.get_user_acl(target))
            acl_set = UserACLSet(self, target, acl_data)

            prop_data = (yield from self.proto_store.get_user_property(
                target))
            prop_set = UserPropertySet(self, target, prop_data)

            return User(self, target, u_data['gecos'], acl_set, prop_set)
