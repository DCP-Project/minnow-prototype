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
from storage import UserStorage, GroupStorage
from settings import *
from errors import *
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

        self.user_store = UserStorage()

        self.line_queue = deque()

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

        if fatal:
            proto = getattr(dest, 'proto', dest)
            logger.debug('Fatal error encountered for client %r (%s: %s [%r])',
                         proto.peername, command, reason, extargs)

        proto.error(command, reason, fatal, extargs, source)

    def _get_func(self, proto, line):
        command = line.command.replace('-', '_').lower()
        func = getattr(self, 'cmd_' + command, None)
        if func is None:
            self.error(proto, line.command, 'No such command', False)
            return

        req = func.__annotations__.get('return', SIGNON)
        if req & SIGNON:
            if not proto.user:
                self.error(proto, line.command, 'You are not registered',
                            False)
                return
        elif req & UNREG:
            if proto.user:
                self.error(proto, line.command, 'This command is only ' \
                            'usable before registration', False)
                return

        return func

    @asyncio.coroutine
    def process(self):
        while True:
            self.waiter = asyncio.Future()
            yield from self.waiter
            while len(self.line_queue):
                proto, line = self.line_queue.popleft()
                proto_or_user = (proto.user if proto.user else proto)
                try:
                    func = self._get_func(proto, line)
                    if not func: continue
                    res = func(proto_or_user, line)
                    if (isinstance(res, asyncio.Future) or
                        inspect.isgenerator(res)):
                        yield from res
                except (UserError, GroupError) as e:
                    logger.warn('Possible bug hit! (Exception below)')
                    traceback.print_exc()
                    self.error(proto, line.command, str(e), False)
                except Exception as e:
                    logger.exception('Bug hit! (Exception below)')
                    self.error(proto, line.command, 'Internal server ' \
                            'error (this isn\'t your fault)')

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

        if self.user_store.get(name) is not None:
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
        self.user_store.add(name, password, gecos, set())

        return True

    def user_motd(self, user):
        if not self.motd:
            user.send(self, user, 'motd', {})
            return

        kval = {
            'text' : [self.motd],
        }
        user.send_multipart(self, user, 'motd', ['text'], kval)

    def cmd_signon(self, proto, line) -> UNREG:
        if self.servpass:
            rservpass = line.kval.get('servpass', [None])[0]
            if rservpass != self.servpass:
                self.error(proto, line.command, 'Bad server password')
                return

        name = line.kval.get('handle', [None])[0]
        if name is None:
            self.error(proto, line.command, 'No handle')
            return

        if valid_handle.match(name) is None:
            self.error(proto, line.command, 'Invalid handle', True,
                       {'handle' : [name]})
            return

        if len(name) > parser.MAXTARGET:
            self.error(proto, line.command, 'Handle is too long', True,
                       {'handle' : [name]})
            return

        # Retrieve the user info
        uinfo = self.user_store.get(name)
        if uinfo is None:
            self.error(proto, line.command, 'You are not registered with ' \
                       'the server', False, {'handle' : [name]})
            return

        password = crypt(line.kval.get('password', ['*'])[0], uinfo.hash)
        if not compare_digest(password, uinfo.hash):
            self.error(proto, line.command, 'Invalid password')
            return

        if name in self.users:
            # TODO - burst all state to the user
            self.error(proto, line.command, 'No multiple users at the '\
                       'moment', True, {'handle' : [name]})
            return

        options = line.kval.get('options', [])

        yield from self.user_enter(proto, name, uinfo.gecos, uinfo.acl,
                                   uinfo.config, options)

    def cmd_register(self, proto, line) -> UNREG:
        if self.servpass:
            rservpass = line.kval.get('servpass', [None])[0]
            if rservpass != self.servpass:
                self.error(proto, line.command, 'Bad server password')
                return

        if not allow_register:
            self.error(proto, line.command, 'Direct registrations are not ' \
                       'permitted on this server')
            return

        name = line.kval.get('handle', [None])[0]
        gecos = line.kval.get('gecos', [name])[0]
        password = line.kval.get('password', [None])[0]

        if not self.user_register(proto, name, gecos, password):
            return

        kval = {
            'handle' : [name],
            'gecos' : [gecos],
            'message' : ['Registration successful, beginning signon'],
        }
        proto.send(self, None, line.command, kval)

        options = line.kval.get('options', [])

        yield from self.user_enter(proto, name, gecos, None, None, options)

    def cmd_fregister(self, user, line) -> SIGNON:
        if acl.UserACLValues.user_register not in user.acl:
            self.error(user, line.command, 'No permission', False)
            return

        name = line.kval.get('handle', [None])[0]
        gecos = line.kval.get('gecos', [name])[0]
        password = line.kval.get('password', [None])[0]

        if not self.user_register(user, name, gecos, password):
            return

        kval = {
            'handle' : [name],
            'gecos' : [gecos],
            'message' : ['Registration successful'],
        }
        proto.send(self, None, line.command, kval)

    def cmd_message(self, user, line) -> SIGNON:
        proto = user.proto
        target = line.target
        if target == '*':
            self.error(user, line.command, 'No valid target', False)
            return

        # Lookup the target...
        if target.startswith(('=', '&')):
            self.error(user, line.command, 'Cannot message servers yet, sorry',
                       False, {'target' : [target]})
            return
        elif target.startswith('#'):
            if target not in self.groups:
                self.error(user, line.command, 'No such group', False,
                           {'target' : [target]})
                return

            target = self.groups[target]
        else:
            if target not in self.users:
                self.error(user, line.command, 'No such user', False,
                           {'target' : [target]})
                return

            target = self.users[target]

        # Get our message
        message = line.kval.get('body', [''])

        # Bam
        target.message(user, message)

    def cmd_motd(self, user, line) -> SIGNON:
        self.user_motd(user)

    def cmd_whois(self, user, line) -> SIGNON:
        target = line.target
        if target == '*' or target.startswith(('=', '#')):
            self.error(user, line.command, 'No valid target', False)
            return

        if target not in self.users:
            self.error(user, line.command, 'No such user', False)
            return

        user = self.users[target]

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

    def cmd_group_enter(self, user, line) -> SIGNON:
        target = line.target
        if target == '*':
            self.error(user, line.command, 'No valid target', False)
            return

        if not target.startswith('#'):
            self.error(user, line.command, 'Invalid group', False,
                       {'target' : [target]})
            return

        if len(target) > parser.MAXTARGET:
            self.error(user, line.command, 'Group name too long', False,
                       {'target' : [target]})
            return

        if target not in self.groups:
            logger.info('Creating group %s', target)
            self.groups[target] = Group(target)

        group = self.groups[target]
        if group in user.groups:
            assert user in group.users
            self.error(user, line.command, 'You are already entered', False,
                       {'target' : [target]})
            return

        group.member_add(user, line.kval.get('reason', [''])[0])

    def cmd_group_exit(self, user, line) -> SIGNON:
        target = line.target
        if target == '*':
            self.error(user, line.command, 'No valid target', False)
            return

        if not target.startswith('#') or target not in self.groups:
            self.error(user, line.command, 'Invalid group', False,
                       {'target' : [target]})
            return

        group = self.groups[target]
        if group not in user.groups:
            assert user not in group.users
            self.error(user, line.command, 'You are not in that group', False,
                       {'target' : [target]})
            return

        group.member_del(user, line.kval.get('reason', ['']))

    def cmd_pong(self, user, line) -> SIGNON:
        user.timeout = False

    def ping_timeout(self, user) -> SIGNON:
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

    def conn_timeout(self, proto) -> UNREG:
        if proto.user:
            # They've signed on
            proto.callbacks.pop('signon', None)
            return

        self.error(proto, '*', 'Connection timed out')

