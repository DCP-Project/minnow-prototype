#!/usr/bin/env python3

import asyncio, ssl
import logging

from functools import partial

from server import DCPServer
from proto import DCPProto, DCPJSONProto
from config import *

logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

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
    loop.create_server(partial(DCPJSONProto, state), *listen_json, ssl=ctx)
]
done, pending = loop.run_until_complete(asyncio.wait(coro))
logger.info('Serving on %r', listen)
logger.info('Serving JSON on %r', listen_json)

try:
    loop.run_forever()
except KeyboardInterrupt:
    logger.info('Exiting from ctrl-c')
finally:
    for server in done: server.cancel()
    loop.close()