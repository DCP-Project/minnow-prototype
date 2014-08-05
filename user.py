from math import ceil
from random import uniform
from config import UserConfig
from acl import UserACL

class User:
    def __init__(self, proto, name, gecos, acl=None, config=None, roster=None,
                 options=[]):
        self.proto = proto
        self.name = name
        self.gecos = gecos
        self.acl = acl
        self.config = config
        self.roster = roster
        self.options = options

        self.sessions = set()
        self.groups = set()

        if self.acl is None:
            self.acl = UserACL()

        if self.config is None:
            self.config = UserConfig()

    def send(self, source, target, command, kval=None):
        if kval is None:
            kval = {}

        self.proto.send(source, target, command, kval)

    def send_multipart(self, source, target, command, keys=[], kval=None):
        self.proto.send_multipart(source, target, command, keys, kval)

    def message(self, source, message):
        self.send(source, self, 'message', {'body' : message})

    def call_later(self, name, delay, callback, *args):
        return self.proto.call_later(name, delay, callback, *args)

    def call_at(self, name, when, callback, *args):
        return self.proto.call_at(name, when, callback, *args)

    def call_ish(self, name, when1, when2, callback, *args):
        return self.proto.call_ish(name, when1, when2, callback, *args)

    def __hash__(self):
        return hash((hash(self.name), hash(self.gecos)))
