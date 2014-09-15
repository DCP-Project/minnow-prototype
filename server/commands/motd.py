# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

from server.command import Command, register

import asyncio


class MOTD(Command):
    @asyncio.coroutine
    def registered(self, server, user, proto, line):
        server.user_MOTD(user)


register['motd'] = MOTD()
