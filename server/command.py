# Command doodads

import logging
from importlib import import_module

from server.errors import *

logger = logging.getLogger(__name__)


class Command:
    def unregistered(self, server, proto, line):
        "Execute this action for unregistered users"
        if id(Command.registered) != id(self.registered):
            raise RegisteredOnlyError('This command is for registered users '
                                      'only')
        raise CommandNotImplementedError('Command not found')

    def registered(self, server, user, proto, line):
        "Execute this action for registered users"
        if id(Command.unregistered) != id(self.unregistered):
            raise UnregisteredOnlyError('This command is for unregistered '
                                        'users only')
        raise CommandNotImplementedError('Command not found')

    def sts(self, server, remote, proto, line):
        "Execute this action for server-to-server"
        raise CommandNotImplementedError('Command not found')

    def ipc(self, server, proto, line):
        "Execute an action for IPC commands"
        raise CommandNotImplementedError('Command not found')


register = dict()
command_mod = list()

# Late import to allow this module to initalise
from server import commands
for mod in commands.__all__:
    command_mod.append(import_module("server.commands." + mod))

logger.info("%d commands loaded", len(register))
