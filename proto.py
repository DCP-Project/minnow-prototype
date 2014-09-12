#!/usr/bin/env python3

import asyncio, socket
import random

import logging
import traceback

from server import DCPServer
from user import User
from group import Group
from settings import *
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

        # User state
        self.user = None

        # Callbacks
        self.callbacks = dict()

        self.peername = None
        self.host = None

        self.transport = None

        self.rdns = asyncio.Future()

        # Multipart storage stuff
        self.multipart = dict()

    def set_host(self, future):
        if future.cancelled():
            return
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

        if self.user:
            self.server.user_exit(self.user, self)

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

        for line in data.split(self.frame.terminator):
            try:
                frame = self.frame.parse(data)
            except ParserError as e:
                logger.exception('Parser failure')
                self.error('*', 'Parser failure', {'cause' : [str(e)]}, False)
                continue

            asyncio.async(self.server.line_queue.put((self, frame)))

    @staticmethod
    def _proto_name(target):
        if isinstance(target, DCPServer):
            return '=' + target.name
        elif hasattr(target, 'name'):
            # XXX for now # is implicit with Group.
            # this is subject to change
            return target.name
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

    def send_multipart(self, source, target, command, keys=[], kval=None):
        if kval is None:
            # No point
            self.send(source, target, command, kval)
            return

        exempt_keys = ('multipart', 'part', 'total')
        if not keys:
            keys = {k for k in kval.keys() if k not in exempt_keys}

        if len(keys) > 1:
            keys.extend(exempt_keys)

            # Copy all unrelated keys
            kval2 = {k : v for k, v in kval.items() if k not in keys}
            for key in keys:
                # Temporarily copy
                kval2[key] = kval[key]

                # Send off
                self.send_multipart(source, target, command, [key], kval2)

                # Delete after use
                del kval2[key]

            return
        else:
            key = keys[0]

        kval = kval.copy()
        sname = source.name
        tname = target.name

        # Strip the list
        data = ''.join(kval[key])
        datalen = len(data)

        kval['multipart'] = [key]

        # This is only a rough guess, to get the number of digits
        # required to store the total.
        kval['total'] = kval['size'] = [str(datalen)]

        fit = self.frame._generic_len(sname, tname, command, kval) - 1
        if fit >= datalen:
            # No point in using multipart
            del kval['multipart']
            del kval['total']
            del kval['size']
            self.send(source, target, command, kval)
            return
        else:
            # Fit our data
            plen = datalen + fit # Actually subtraction
            split = [data[0+i:plen+i] for i in range(0, datalen, plen)]
            kval['total'] = [str(len(split))]
            for part, data in enumerate(split):
                kval[key] = [data]
                self.send(source, target, command, kval)

                # Not needed anymore
                # XXX recompute optimal size
                del kval['total']
                del kval['size']

    def error(self, command, reason, fatal=True, extargs=None, source=None):
        if not self.transport:
            return

        kval = {
            'command' : [command],
            'reason' : [reason],
        }
        if extargs:
            kval.update(extargs)

        if not source:
            source = self.server

        self.send(source, self.user, 'error', kval)

        if fatal:
            self.transport.close()

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


class DCPProto(DCPBaseProto):
    def __init__(self, server):
        super().__init__(server, parser.Frame)


class DCPJSONProto(DCPBaseProto):
    def __init__(self, server):
        super().__init__(server, parser.JSONFrame)

