from collections import defaultdict

class DCPGroup:
    """ Like an IRC channel """
    def __init__(self, proto, name, topic=None, acl=None):
        self.proto = proto
        self.name = name
        self.topic = topic
        self.acl = acl
        self.members = set()

        if acl is None:
            self.acl = {}

        if not self.name.startswith('#'):
            self.name = '#' + self.name

    def member_add(self, user, reason=None):
        if user in self.members:
            raise Exception('Duplicate addition')

        self.members.add(user)

        kval = defaultdict(list)
        if reason:
            kval['reason'].append(reason)

        self.send(user.handle, self.name, 'group-enter', kval)

    def member_del(self, user, reason=None):
        self.members.remove(user)

        kval = defaultdict(list)
        if reason:
            kval['reason'].append(reason)

        self.send(user.handle, self.name, 'group-exit', kval)

    def message(self, user, message):
        # TODO various ACL checks
        if user not in self.members:
            raise Exception('User not in group')

        kval = defaultdict(list)
        kval['message'].append(message)

        self.send(self.name, user.handle, 'message', kval, [user])

    def send(self, source, target, command, kval=None, filter=[]):
        for user in self.members:
            if user in filter:
                continue

            self.user.send(source, target, self.name, command, kval)
