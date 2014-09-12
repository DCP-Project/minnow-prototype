# Command doodads

import logging
from importlib import import_module

from server.errors import *

logger = logging.getLogger(__name__)


class Command:
    def unregistered(self, server, proto, line):
        "Execute this action for unregistered users"
        raise CommandNotImplementedError

    def registered(self, server, user, proto, line):
        "Execute this action for registered users"
        raise CommandNotImplementedError

    def sts(self, server, remote, line):
        "Execute this action for server-to-server"
        raise CommandNotImplementedError

    def ipc(self, server, line):
        "Execute an action for IPC commands"
        raise CommandNotImplementedError


register = dict()
command_mod = list()

# Late import to allow this module to initalise
from server import commands
for mod in commands.__all__:
    command_mod.append(import_module("server.commands." + mod))

logger.info("%d commands loaded", len(register))

