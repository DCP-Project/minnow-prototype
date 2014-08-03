import enum
import time
import asyncio
import re
import inspect
from collections import deque
from functools import partial

from random import randint

from crypt import crypt, mksalt
from hmac import compare_digest
import logging
import traceback

from user import User
from group import Group
from storage import AsyncStorage, ProtocolStorage
from settings import *
from errors import *

import command
import parser
import acl
import config

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# This is subject to change
valid_handle = re.compile(r'^[^#!=&$,\?\*\[\]][^=$,\?\*\[\]]+$')

# Flags for the annotations
UNREG = 1
SIGNON = 2

class DCPServer:
    def __init__(self, name, servpass=servpass):
        self.name = name
        self.servpass = servpass

        self.users = dict()
        self.groups = dict()

        self.user_store = AsyncStorage(ProtocolStorage, 'store.db')

        self.line_queue = asyncio.Queue()

        self.motd = None
        self.motd_load()

        # Start this loop
        asyncio.Task(self.process())

    def motd_load(self):
        try:
            with open('motd.txt', 'r') as f:
                self.motd = ''.join(f.readlines())
        except Exception as e:
            logger.exception('Could not read MOTD')

    def error(self, dest, command, reason, fatal=True, extargs=None,
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
                         proto.peername, command, reason, extargs)

        proto.error(command, reason, fatal, extargs, source)

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

    def user_enter(self, proto, name, gecos, acl, config, options):
        user = User(proto, name, gecos, acl, config, None, options)
        proto.user = self.users[name] = user

        # Cancel the timeout
        proto.callbacks['signon'].cancel()
        del proto.callbacks['signon']

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
        self.ping_timeout(user)

    def user_exit(self, user):
        if user is None:
            return

        del self.users[user.name]

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

        f = yield from self.user_store.get_user(name)
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

        password = crypt(password, mksalt())

        # Bang
        asyncio.Task(self.user_store.create_user(name, password, gecos))

        return True

    def user_motd(self, user):
        if not self.motd:
            user.send(self, user, 'motd', {})
            return

        kval = {
            'text' : [self.motd],
        }
        user.send_multipart(self, user, 'motd', ['text'], kval)

    def ping_timeout(self, user):
        if user.timeout:
            logger.debug('User %r timed out', user.proto.peername)
            self.error(user, 'ping', 'Ping timeout')
            return

        user.send(self, user, 'ping', {'time' : [str(round(time.time()))]})

        user.timeout = True

        loop = asyncio.get_event_loop()
        sched = randint(4500, 6000) / 100
        cb = loop.call_later(sched, self.ping_timeout, user)
        user.proto.callbacks['ping'] = cb

    def conn_timeout(self, proto):
        if proto.user:
            # They've signed on
            proto.callbacks.pop('signon', None)
            return

        self.error(proto, '*', 'Connection timed out')

