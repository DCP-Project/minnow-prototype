from collections import defaultdict

class Roster:
    # TODO
    pass

class User:
    def __init__(self, proto, name, gecos, roster, options):
        self.proto = proto
        self.name = name
        self.gecos = gecos
        self.roster = roster
        self.options = options

        self.sessions = set()
        self.groups = set()

        self.acl = set()
        self.property = dict()

    def send(self, source, target, command, kval=None):
        if kval is None:
            kval = defaultdict(list)

        self.proto.send(source, target, command, kval)

    def message(self, source, message):
        self.send(source, self, 'message', {'body' : message})

    def has_acl(self, acl):
        return acl in self.acl

    def set_acl(self, acl):
        self.acl.add(acl)

    def del_acl(self, acl):
        self.acl.discard(acl)

    def has_property(self, property):
        return property in self.property

    def get_property(self, property):
        return self.property[property]

    def set_property(self, property, value=None):
        self.property[property] = value

    def del_property(self, property):
        self.property.pop(property, None)

    def __hash__(self):
        return hash((hash(self.name), hash(self.gecos)))
