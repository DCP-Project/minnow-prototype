#!/usr/bin/env python3

import time
import asyncio
import re

from crypt import crypt, mksalt
from hmac import compare_digest
import ssl

from user import User
from group import Group
from storage import UserStorage
from config import *
from errors import *
import parser

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

    def error(self, dest, command, reason, fatal=True, extargs=None):
        if hasattr(dest, 'proto'):
            proto = dest.proto
        elif hasattr(dest, 'error'):
            proto = dest

        if fatal:
            proto = getattr(dest, 'proto', dest)
            peername = proto.transport.get_extra_info('peername')
            print('Fatal error encountered for client {} ({}: {} [{}])'.format(
                peername, command, reason, extargs))

        proto.error(command, reason, fatal, extargs)

    def process(self, proto, data):
        # Turn a protocol into a user
        for line in parser.Frame.parse(data):
            command = line.command.replace('-', '_')
            func = getattr(self, 'cmd_' + command, None)
            if func is None:
                self.error(proto, command, 'No such command', False)
                return

            req = func.__annotations__.get('return', SIGNON)
            if req & SIGNON:
                if not proto.user:
                    self.error(proto, line.command, 'You are not registered',
                               False)
                    return

                proto_or_user = proto.user
            elif req & UNREG:
                if proto.user:
                    self.error(proto, line.command, 'This command is only ' \
                               'usable before registration', False)
                    return

                proto_or_user = proto

            try:
                # XXX not sure I like this proto_or_user hack
                func(proto_or_user, line)
            except Exception as e:
                print('Uh oh! We got an error!')
                self.error(proto_or_user, line.command, 'Internal server ' \
                           'error')
                raise e
            
    def user_exit(self, user):
        if user is None:
            return

        del self.users[user.name]

        for group in user.groups:
            # Part them from all groups
            group.member_del(user, permanent=True)

    def cmd_signon(self, proto, line) -> UNREG:
        name = line.kval.get('handle', [None])[0]
        if name is None:
            self.error(proto, line.command, 'No handle')
            return

        if valid_handle.match(name) is None:
            self.error(proto, line.command, 'Invalid handle', True,
                       {'handle' : [name]})
            return

        if len(name) > 48:
            self.error(proto, line.command, 'Handle is too long', True,
                       {'handle' : [name]})
            return

        # Retrieve the user info
        uinfo = self.user_store.get(name)
        if uinfo is None:
            self.error(proto, line.command, 'You are not registered with ' \
                       'the server', True, {'handle' : [name]})
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

        user = User(proto, name, uinfo.gecos, set(), options)
        proto.user = self.users[name] = user

        kval = {
            'name' : [self.name],
            'time' : [str(round(time.time()))],
            'version': ['Minnow prototype server', 'v0.1-prealpha'],
            'options' : [],
        }
        user.send(self, user, 'signon', kval)

    def cmd_register(self, proto, line) -> UNREG:
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
            self.error(proto, line.command, 'Invalid handle', False,
                       {'handle' : [name]})
            return

        if len(name) > 48:
            self.error(proto, line.command, 'Handle is too long', False,
                       {'handle' : [name]})
            return

        if self.user_store.get(name) is not None:
            self.error(proto, line.command, 'Handle already registered', False,
                       {'handle' : [name]})
            return

        gecos = line.kval.get('gecos', [name])[0]
        if len(gecos) > 48:
            self.error(proto, line.command, 'GECOS is too long', False,
                       {'gecos' : [gecos]})
            return

        password = line.kval.get('password', [None])[0]
        if password is None or len(password) < 5:
            # Password is not sent back for security reasons
            self.error(proto, line.command, 'Bad password', False)
            return

        password = crypt(password, mksalt())

        # Bang
        self.user_store.add(name, password, gecos, set())

        kval = {
            'handle' : [name],
            'gecos' : [gecos],
            'message' : ['Registration successful, beginning signon'],
        }
        proto.send(self, None, line.command, kval)

        self.cmd_signon(proto, line)

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

    def cmd_group_enter(self, user, line) -> SIGNON:
        target = line.target
        if target == '*':
            self.error(user, line.command, 'No valid target', False)
            return

        if not target.startswith('#'):
            self.error(user, line.command, 'Invalid group', False,
                       {'target' : [target]})
            return

        if len(target) > 48:
            self.error(user, line.command, 'Group name too long', False,
                       {'target' : [target]})
            return

        if target not in self.groups:
            print('Creating group {}'.format(target))
            self.groups[target] = Group(proto, target)

        group = self.groups[target]
        if group in user.groups:
            assert user in group.users
            self.error(user, line.command, 'You are already entered', False,
                       {'target' : [target]})
            return

        group.member_add(user, line.kval.get('reason', ['']))

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

server = DCPServer(servname)

class DCPProto(asyncio.Protocol):
    """ This is the asyncio connection stuff...

    Everything should just call back to the main server/user stuff here.
    """

    def __init__(self):
        self.__buf = b''
        
        # Global state
        self.server = server

        # User state
        self.user = None

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('connection from {}'.format(peername))
        self.transport = transport

    def connection_lost(self, exc):
        peername = self.transport.get_extra_info('peername')
        print('connection lost from {} (reason {})'.format(peername, exc))

        self.server.user_exit(self.user)

    def data_received(self, data):
        data = self.__buf + data

        if not data.endswith(b'\x00\x00'):
            data, sep, self.__buf = data.rpartition(b'\x00\x00')
            if sep:
                data += sep
            else:
                self.__buf = data
                return

        server.process(self, data)

    @staticmethod
    def _proto_name(target):
        if isinstance(target, (User, Group, DCPProto)):
            # XXX for now # is implicit with Group.
            # this is subject to change
            return target.name
        elif isinstance(target, DCPServer):
            return '=' + server.name
        elif target is None:
            return '*'
        else:
            return '&' + getattr(target, 'name', target)

    def send(self, source, target, command, kval=None):
        source = self._proto_name(source)
        target = self._proto_name(target)
        if kval is None: kval = dict()

        frame = parser.Frame(source, target, command, kval)
        self.transport.write(bytes(frame))

    def error(self, command, reason, fatal=True, extargs=None):
        kval = {
            'command' : [command],
            'reason' : [reason],
        }
        if extargs:
            kval.update(extargs)

        self.send(self.server, self.user, 'error', kval)

        if fatal:
            self.transport.close()

# Set up SSL context
ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
ctx.load_default_certs(ssl.Purpose.CLIENT_AUTH)
ctx.load_cert_chain('cert.pem')

ctx.options &= ~ssl.OP_ALL
ctx.options |= ssl.OP_SINGLE_DH_USE | ssl.OP_SINGLE_ECDH_USE
ctx.options |= (ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 |
                ssl.OP_NO_TLSv1_1)
ctx.options |= ssl.OP_NO_COMPRESSION

loop = asyncio.get_event_loop()
coro = loop.create_server(DCPProto, *listen, ssl=ctx)
_server = loop.run_until_complete(coro)
print('serving on {}'.format(_server.sockets[0].getsockname()))

try:
    loop.run_forever()
except KeyboardInterrupt:
    print("exit")
finally:
    _server.close()
    loop.close()
