# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio
import socket
import random

import logging
import traceback

from sys import stderr
from collections import defaultdict

import server.parser as parser

from server.server import DCPServer
from server.errors import *
from settings import *

if globals().get('listen_websockets'):
    try:
        import websockets
    except ImportError:
        print('WebSocket support requested, but websockets module not found',
              file=stderr)
        print('Get it at http://github.com/aaugustin/websockets', file=stderr)

        websockets = None

logger = logging.getLogger(__name__)


@asyncio.coroutine
def rdns_check(ip, future):
    loop = asyncio.get_event_loop()
    try:
        host = (yield from loop.getnameinfo((ip, 0), socket.NI_NUMERICSERV))[0]
        res = yield from loop.getaddrinfo(host, None, family=socket.AF_UNSPEC,
                                          type=socket.SOCK_STREAM,
                                          proto=socket.SOL_TCP)
        if future.cancelled():
            return
        future.set_result(host if ip in (x[4][0] for x in res) else ip)
    except Exception as e:
        logger.info('DNS resolver error')
        traceback.print_exc()
        if future.cancelled():
            return
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

        # Multipart storage stuff
        self.multipart = dict()

        # Callbacks storage
        self.callbacks = dict()

        self.transport = None

        # Line queue
        self.recvq = asyncio.Queue()

    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        logger.info('Connection from %s', self.peername)

        self.transport = transport
        asyncio.async(self.process())

    def connection_lost(self, exc):
        logger.info('Connection lost from %r (reason %s)', self.peername,
                    str(exc))

        for callback in self.callbacks.values():
            callback.cancel()

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

        data = data.split(self.frame.terminator)[:-1]
        for line in data:
            try:
                frame = self.frame.parse(line)
            except ParserError as e:
                logger.exception('Parser failure')
                self.error('*', 'Parser failure', {'cause': [str(e)]})
                break

            asyncio.async(self.recvq.put(frame))

    @asyncio.coroutine
    def process(self):
        while True:
            line = (yield from self.recvq.get())
            print('Line received from the wire', line)
            try:
                yield from self.server._call_func(self, line)
            except Exception as e:
                logger.exception('Bug hit! (Exception below)')
                self.error(line.command, 'Internal server error (this isn\'t '
                           'your fault)')
                break

            if self.transport is None:
                break

    @staticmethod
    def _proto_name(target):
        if isinstance(target, DCPServer):
            return '=' + target.name
        elif hasattr(target, 'name'):
            # XXX for now # is implicit with Group.
            # this is subject to change
            return target.name
        elif target is None or target == '*':
            return '*'
        else:
            return '&' + getattr(target, 'name', target)

    def send(self, source, target, command, kval=None):
        if not self.transport:
            return

        source = self._proto_name(source)
        target = self._proto_name(target)
        if kval is None:
            kval = dict()

        frame = self.frame(source, target, command, kval)
        self.transport.write(bytes(frame))

    def send_multipart(self, source, target, command, keys=list(), kval=None,
                       use_size=False):
        if kval is None:
            # No point
            self.send(source, target, command, {})
            return

        sname = source.name
        tname = target.name

        if any(k in ('multipart', 'transfer-size') for k in keys):
            raise MultipartKeyError('Bad multipart keys')
        elif not keys:
            keys = [k for k in kval.keys()]

        len_k = len(keys)

        # Now we get two dictionaries
        # kval_first is the dictionary containing all keys we send on the
        # first frame
        # kval_k is the dictionary containing all the multipart keys
        kval_first = dict()
        kval_k = dict()
        for k, v in kval.items():
            if k in keys:
                kval_k[k] = v
            else:
                kval_first[k] = v

        if use_size:
            kval_first['multipart'] = keys

            # Length of the pieces
            # We will send each multipart key at once, til its all sent
            # If it should/must be sent separate, tough (for now).
            p_len = parser.MAXFRAME // len_k

            # Split up the keys
            # kval_s - scratch space (coalesced keys)
            kval_s = {k: ''.join(v) for v in kval_k.items()}
            kval_k = defaultdict(list)  # Erase for now
            while len_k > 0:
                kval_s_del = []
                for k, v in kval_s.items():
                    v_len = len(v)

                    split_len = (p_len if v_len >= p_len else v_len)
                    s = v[:split_len]

                    if s:
                        kval_k[k].append(s)

                    if v_len > split_len:
                        # Store remaining string if we have it
                        kval_s[k] = v[split_len:]
                    else:
                        # Exhausted this key, so remove it
                        kval_s_del.append(k)

                        len_k -= 1
                        if len_k > 0 and not s:
                            p_len = parser.MAXFRAME // len_k
                        else:
                            # No more pieces
                            break

                for k in kval_s_del:
                    del kval_s[k]

            # Get the transfer size
            kval_first['transfer-size'] = str(sum(sum(len(v2) for v2 in v) for
                                                  v in kval_k.values()))

        self.send(source, target, command, kval_first)

        # The goal of the below is to pack as much data as possible into a
        # single frame.

        stub_k = {k: ['*'] for k in keys}

        # Get the length that will fit
        fit = self.frame._generic_len(sname, tname, command, stub_k)
        fit -= len_k  # Minus stub value lengths

        # It won't fit. Punt.
        if fit >= parser.MAXFRAME:
            raise MultipartOverflowError()

        kval_cur = defaultdict(list)
        kval_next = defaultdict(list)
        cur_len = 0
        len_kv = self.frame.len_kv
        while kval_k:
            del_list = []
            for k, v in kval_k.items():
                kval_next[k].append(v[0])
                del v[0]
                if not len(v):
                    del_list.append(k)

            if (fit + len_kv(kval_cur) + len_kv(kval_next)) >= parser.MAXFRAME:
                # Send what we have, replace kval_cur
                self.send(source, target, command, kval_cur)

                kval_cur.clear()

            for k, v in kval_next.items():
                kval_cur[k].extend(v)

            kval_next.clear()

            for k in del_list:
                del kval_k[k]

        if kval_cur:
            # Send whatever we have left
            self.send(source, target, command, kval_cur)

        # End of stream sentinel
        self.send(source, target, command, {'multipart': ['*']})

    def error(self, command, reason, fatal=True, extargs=None, source=None):
        if not self.transport:
            return

        kval = {
            'command': [command],
            'reason': [reason],
        }
        if extargs:
            kval.update(extargs)

        if not source:
            source = self.server

        target = getattr(self, 'user', getattr(self, 'remote', '*'))
        self.send(source, target, 'error', kval)

        if fatal:
            self.transport.close()
            self.transport = None

    def call_cancel(self, name):
        callback = self.callbacks.pop(name, None)
        if callback is None:
            return

        callback.cancel()

    def call_later(self, name, delay, callback, *args):
        loop = asyncio.get_event_loop()
        self.callbacks[name] = loop.call_later(delay, callback, *args)
        return self.callbacks[name]

    def call_at(self, name, when, callback, *args):
        loop = asyncio.get_event_loop()
        self.callbacks[name] = loop.call_at(when, callback, *args)
        return self.callbacks[name]

    def call_ish(self, name, when1, when2, callback, *args):
        delay = round(random.uniform(when1, when2), 3)
        return self.call_later(name, delay, callback, *args)


class DCPSocketProto(DCPBaseProto):
    def __init__(self, server, frame):
        super().__init__(server, frame)

        # User state
        self.user = None

        self.peername = None
        self.host = None

        self.rdns = asyncio.Future()

    def set_host(self, future):
        if future.cancelled():
            return
        logger.info('Host for %r set to [%s]', self.peername, future.result())
        self.host = future.result()

    def connection_made(self, transport):
        super().connection_made(transport)

        self.host = self.peername[0]

        # Begin DNS lookup
        self.rdns.add_done_callback(self.set_host)
        dns = asyncio.wait_for(rdns_check(self.peername[0], self.rdns), 5)
        asyncio.async(dns)

        # Start the connection timeout
        loop = asyncio.get_event_loop()
        cb = loop.call_later(60, self.server.conn_timeout, self)
        self.callbacks['signon'] = cb

    def connection_lost(self, exc):
        super().connection_lost(exc)

        self.rdns.cancel()

        if self.user:
            self.server.user_exit(self.user, self)


class DCPProto(DCPSocketProto):
    def __init__(self, server):
        super().__init__(server, parser.Frame)


class DCPJSONProto(DCPSocketProto):
    def __init__(self, server):
        super().__init__(server, parser.JSONFrame)


class DCPUnixProto(DCPBaseProto):
    def __init__(self, server):
        super().__init__(server, parser.JSONFrame)


class WebSocketsWrapper:
    """Crummy wrapper around the websockets lib to fake a proto.

    It really sucks but it's the best way atm."""

    def connection_made(self, transport):
        logger.info("Connection made", transport)
        self.transport = transport

    def connection_closed(self, exc):
        logger.info("Connection closed")

    def data_received(self, data):
        logger.info("Got some data!", data)
        self.transport.write(data)

    def __call__(self, websocket, path):
        def write(data):
            data = data.decode('utf-8', 'replace')
            asyncio.async(websocket.send(data))

        def close():
            data = data.decode('utf-8', 'replace')
            asyncio.async(websocket._real_close())

        websocket.write = write
        websocket._real_close = websocket.close
        websocket.close = close
        self.connection_made(websocket)
        while True:
            message = yield from websocket.recv()
            if not message:
                self.connection_closed(None)
                break

            self.data_received(message.encode('utf-8', 'replace'))


class DCPWebSocketsProto(DCPJSONProto, WebSocketsWrapper):
    pass
