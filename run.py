#!/usr/bin/env python3
# coding: utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio
import ssl
import logging
import os

from functools import partial

from server.server import DCPServer
from server.proto import (DCPProto, DCPJSONProto, DCPUnixProto,
                          DCPWebSocketsProto)
from settings import *

if globals().get('listen_websockets'):
    try:
        import websockets
    except ImportError:
        websockets = None

# Set a restrictive umask
os.umask(0o077)

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

try:
    os.unlink(unix_path)
except OSError:
    pass

# Set up SSL context
ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
ctx.load_default_certs(ssl.Purpose.CLIENT_AUTH)
ctx.load_cert_chain('cert.pem')

# SSL options
ctx.options &= ~ssl.OP_ALL
ctx.options |= ssl.OP_SINGLE_DH_USE | ssl.OP_SINGLE_ECDH_USE
ctx.options |= (ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 |
                ssl.OP_NO_TLSv1_1)
ctx.options |= ssl.OP_NO_COMPRESSION

# Begin event loop initalisation
loop = asyncio.get_event_loop()
state = DCPServer(servname)
coro = [
    loop.create_server(partial(DCPProto, state), *listen, ssl=ctx),
    loop.create_server(partial(DCPJSONProto, state), *listen_json, ssl=ctx),
    loop.create_unix_server(partial(DCPUnixProto, state), unix_path),
]

if websockets is not None:
    coro.append(websockets.serve(partial(DCPWebSocketsProto, state),
                                 *listen_websockets))

done, pending = loop.run_until_complete(asyncio.wait(coro))
logger.info('Serving on %r', listen)
logger.info('Serving JSON on %r', listen_json)
logger.info('Unix control socket at %r', unix_path)

if websockets is not None:
    logger.info('Serving WebSockets on %r', listen_websockets)

try:
    loop.run_forever()
except KeyboardInterrupt:
    logger.info('Exiting from ctrl-c')
finally:
    for server in done:
        server.cancel()
    loop.close()
