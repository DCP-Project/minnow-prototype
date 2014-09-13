import asyncio
import crypt

from server.property import UserProperty
from server.acl import UserACLSet

class User:
    def __init__(self, server, name, gecos, acl=None, property=None,
                 roster=None, options=[]):
        self.server = server
        self.name = name
        self._gecos = gecos
        self.acl = acl
        self.property = property # TODO
        self.roster = roster # TODO
        self.options = options # TODO

        self.sessions = set()
        self.groups = set()

        if self.acl is None:
            self.acl = UserACLSet()

        if self.property is None:
            self.property = UserProperty()

    @property
    def gecos(self):
        return self._gecos

    @gecos.setter
    def gecos(self, value):
        self._gecos = value
        asyncio.async(self.server.proto_store.set_user(self.name,
                      gecos=value))

    @property
    def password(self):
        ret = (yield from self.server.get_user(name))['password']
        return ret

    @password.setter
    def password(self, value):
        if not value.startswith('$'):
            value = crypt.crypt(value, crypt.mksalt())

        asyncio.async(self.server.proto_store.set_user(self.name,
                      password=value))

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
