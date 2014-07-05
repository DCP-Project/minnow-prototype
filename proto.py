#!/usr/bin/env python3

import asyncio, socket

import logging
import traceback

from server import DCPServer
from user import User
from group import Group
from config import *
from errors import *
import parser

logger = logging.getLogger(__name__)

@asyncio.coroutine
def rdns_check(ip, future):
    loop = asyncio.get_event_loop()
    try:
        host = (yield from loop.getnameinfo((ip, 0), socket.NI_NUMERICSERV))[0]
        res = yield from loop.getaddrinfo(host, None, family=socket.AF_UNSPEC,
                                          type=socket.SOCK_STREAM,
                                          proto=socket.SOL_TCP)
        future.set_result(host if ip in (x[4][0] for x in res) else ip)
    except Exception as e:
        logger.info('DNS resolver error')
        traceback.print_exc()
        future.set_result(ip)

class DCPBaseProto(asyncio.Protocol):
    """ This is the asyncio connection stuff...

    Everything should just call back to the main server/user stuff here.
    """

    def __init__(self, server, frame):
        self.__buf = b''

        # Frame factory
        self.frame = frame

        # Global state
        self.server = server

        # User state
        self.user = None

        # Callbacks
        self.callbacks = dict()

        self.peername = None
        self.host = None

        self.transport = None

        self.rdns = asyncio.Future()

    def set_host(self, future):
        logger.info('Host for %r set to [%s]', self.peername, future.result())
        self.host = future.result()

    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        logger.info('Connection from %s', self.peername)

        self.host = self.peername[0]

        self.transport = transport

        # Begin DNS lookup
        self.rdns.add_done_callback(self.set_host)
        dns = asyncio.wait_for(rdns_check(self.peername[0], self.rdns), 5)
        asyncio.Task(dns)

        # Start the connection timeout
        loop = asyncio.get_event_loop()
        cb = loop.call_later(60, self.server.conn_timeout, self)
        self.callbacks['signon'] = cb

    def connection_lost(self, exc):
        logger.info('Connection lost from %r (reason %s)', self.peername, str(exc))

        self.rdns.cancel()

        self.server.user_exit(self.user)

        for cb in self.callbacks.values():
            cb.cancel()

        self.transport = None

    def data_received(self, data):
        data = self.__buf + data

        if not data.endswith(self.frame.terminator):
            data, sep, self.__buf = data.rpartition(self.frame.terminator)
            if sep:
                data += sep
            else:
                self.__buf = data
                return

        for line in data.split(self.frame.terminator):
            try:
                frame = self.frame.parse(data)
            except ParserError as e:
                logger.exception('Parser failure')
                self.error('*', 'Parser failure', {'cause' : [str(e)]}, False)

            self.server.line_queue.append((self, line))

        if not self.server.waiter.done():
            self.server.waiter.set_result(None)

    @staticmethod
    def _proto_name(target):
        if isinstance(target, (User, Group, DCPBaseProto)):
            # XXX for now # is implicit with Group.
            # this is subject to change
            return target.name
        elif isinstance(target, DCPServer):
            return '=' + target.name
        elif target is None:
            return '*'
        else:
            return '&' + getattr(target, 'name', target)

    def send(self, source, target, command, kval=None):
        if not self.transport:
            return

        source = self._proto_name(source)
        target = self._proto_name(target)
        if kval is None: kval = dict()

        frame = self.frame(source, target, command, kval)
        self.transport.write(bytes(frame))

    def error(self, command, reason, fatal=True, extargs=None):
        if not self.transport:
            return

        kval = {
            'command' : [command],
            'reason' : [reason],
        }
        if extargs:
            kval.update(extargs)

        self.send(self.server, self.user, 'error', kval)

        if fatal:
            self.transport.close()


class DCPProto(DCPBaseProto):
    def __init__(self, server):
        super().__init__(server, parser.Frame)


class DCPJSONProto(DCPBaseProto):
    def __init__(self, server):
        super().__init__(server, parser.JSONFrame)

