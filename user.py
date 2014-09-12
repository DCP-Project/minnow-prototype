from math import ceil
from random import uniform
from config import UserConfig
from acl import UserACLSet

class User:
    def __init__(self, server, name, gecos, acl=None, config=None,
                 roster=None, options=[]):
        self.server = server
        self.name = name
        self._gecos = gecos
        self.acl = acl
        self.config = config # TODO
        self.roster = roster # TODO
        self.options = options # TODO

        self.sessions = set()
        self.groups = set()

        if self.acl is None:
            self.acl = UserACLSet()

        if self.config is None:
            self.config = UserConfig()

    @property
    def gecos(self):
        return self._gecos

    @gecos.setter
    def gecos(self, value):
        self._gecos = gecos

    def send(self, source, target, command, kval=None):
        if kval is None:
            kval = {}

        for proto in self.sessions:
            proto.send(source, target, command, kval)

    def send_multipart(self, source, target, command, keys=[], kval=None):
        for proto in self.sessions:
            proto.send_multipart(source, target, command, keys, kval)

    def message(self, source, message):
        self.send(source, self, 'message', {'body' : message})

    def __hash__(self):
        return hash((hash(self.name), hash(self.gecos)))
