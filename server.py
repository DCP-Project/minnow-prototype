# Copyright © 2014 
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

from acl import UserACLSet, GroupACLSet
from user import User
from group import Group
from storage import AsyncStorage, ProtocolStorage
from settings import *
from errors import *

import command
import parser

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

        self.proto_store = AsyncStorage(ProtocolStorage, 'store.db')

        self.line_queue = asyncio.Queue()

        self.motd = None
        self.motd_load()

        # Start this loop
        asyncio.Task(self.process())

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

        if proto.user:
            try:
                yield from instance.registered(self, proto.user, line)
            except CommandNotImplementedError:
                self.error(proto, line.command, 'This command may only be ' \
                    'used before signon', False)
        else:
            # This will have to change later for sts and stuff.
            try:
                yield from instance.unregistered(self, proto, line)
            except CommandNotImplementedError:
                self.error(proto, line.command, 'You are not signed on',
                           False)

    @asyncio.coroutine
    def process(self):
        while True:
            proto, line = (yield from self.line_queue.get())
            try:
                yield from self._call_func(proto, line)
            except (UserError, GroupError) as e:
                logger.warn('Possible bug hit! (Exception below)')
                traceback.print_exc()
                self.error(proto, line.command, str(e), False)
            except Exception as e:
                logger.exception('Bug hit! (Exception below)')
                self.error(proto, line.command, 'Internal server error (this ' \
                        'isn\'t your fault)')

    def user_enter(self, proto, name, options):
        user = self.get_any_target(name)
        proto.user = self.online_users[name] = user

        user.options = options

        # Cancel the timeout
        proto.call_cancel('signon')

        kval = {
            'name' : [self.name],
            'time' : [str(round(time.time()))],
            'version': ['Minnow prototype server', 'v0.1-prealpha'],
            'options' : [],
        }

        yield from proto.rdns
        if proto.host != proto.peername[0]:
            kval['host'] = [proto.host]

        user.send(self, user, 'signon', kval)

        # Send the MOTD
        self.user_motd(user)

        # Ping timeout stuff
        user.timeout = False
        self.ping_timeout(proto)

    def user_exit(self, user):
        if user is None:
            return

        del self.online_users[user.name]

        for group in list(user.groups):
            # Part them from all groups
            group.member_del(user, permanent=True)

    def user_register(self, proto, name, gecos, password):
        if name is None:
            self.error(proto, line.command, 'No handle', False)
            return False

        if valid_handle.match(name) is None:
            self.error(proto, line.command, 'Invalid handle', False,
                       {'handle' : [name]})
            return False

        if len(name) > parser.MAXTARGET:
            self.error(proto, line.command, 'Handle is too long', False,
                       {'handle' : [name]})
            return False

        f = yield from self.proto_store.get_user(name)
        if f is not None:
            self.error(proto, line.command, 'Handle already registered', False,
                       {'handle' : [name]})
            return False

        if len(gecos) > parser.MAXTARGET:
            self.error(proto, line.command, 'GECOS is too long', False,
                       {'gecos' : [gecos]})
            return False

        if password is None or len(password) < 5:
            # Password is not sent back for security reasons
            self.error(proto, line.command, 'Bad password', False)
            return False

        password = crypt.crypt(password, crypt.mksalt())

        # Bang
        asyncio.Task(self.proto_store.create_user(name, password, gecos))

        return True

    def user_motd(self, user):
        if not self.motd:
            user.send(self, user, 'motd', {})
            return

        kval = {
            'text' : [self.motd],
        }
        user.send_multipart(self, user, 'motd', ['text'], kval)

    def ping_timeout(self, proto):
        if proto.timeout:
            logger.debug('Connection %r timed out', proto.peername)
            self.error(proto, 'ping', 'Ping timeout')
            return

        proto.send(self, proto, 'ping', {'time' : [str(round(time.time()))]})

        user.timeout = True

        proto.call_ish('ping', 45, 60, self.ping_timeout, proto)

    def conn_timeout(self, proto):
        if proto.user:
            # They've signed on, no need
            user.call_cancel('signon')
            return

        self.error(proto, '*', 'Connection timed out')

    def get_online_target(self, target):
        if target == '*':
            return

        if target.startswith('#') and target in self.groups:
            return self.groups[target]
        elif target in self.online_users:
            return self.online_users[target]

    @functools.lru_cache(maxsize=max_cache)
    @asyncio.coroutine
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
            acl = (yield from self.proto_store.get_group_acl(target))
            return Group(target, g_data['topic'], GroupACLSet(acl), None,
                         g_data['timestamp'])
        else:
            u_data = (yield from self.proto_store.get_user(target))
            acl = (yield from self.proto_store.get_user_acl(target))
            return User(None, target, u_data['gecos'], UserACLSet(acl))

