# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

from server.entity import Entity
from server.acl import ACLUserList
from server.property import PropertyUserList
from server.datastructure import CaselessDict

class User(Entity):
    def __init__(self, name, gecos, password, acl=None, property=None,
                 roster=None, metadata=None, options=[]):
        self.gecos = gecos

        # hash only!
        self.password = password

        if not acl:
            acl = ACLUserList()

        if not property:
            property = PropertyUserList()

        if not roster:
            roster = RosterList()

        if not metadata:
            metadata = CaselessDict()

        super().__init__(name, acl, property, metadata)

        self.roster = roster
        self.options = options
