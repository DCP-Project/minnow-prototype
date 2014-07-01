from collections import defaultdict

class DCPRoster:
    # TODO
    pass

class DCPUser:
    def __init__(self, proto, name, gecos, roster, options):
        self.proto = proto
        self.name = name
        self.gecos = gecos
        self.roster = roster
        self.options = options
        self.sessions = set()
        self.groups = set()

    def send(self, source, target, command, kval=None):
        if kval is None:
            kval = defaultdict(list)

        self.proto.send(source, target, command, kval)

    def __hash__(self):
        return hash(name) ^ hash(gecos)
