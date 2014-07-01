from collections import defaultdict

class DCPGroup:
    """ Like an IRC channel """
    def __init__(self, proto, name, topic=None, acl=None):
        self.proto = proto
        self.name = name
        self.topic = topic
        self.acl = acl
        self.users = set()

        if acl is None:
            self.acl = defaultdict(list) 

        if not self.name.startswith('#'):
            self.name = '#' + self.name

    def member_add(self, user, reason=None):
        if user in self.users:
            raise Exception('Duplicate addition')

        self.users.add(user)
        user.groups.add(self)

        kval = defaultdict(list)
        if reason:
            kval['reason'].append(reason)

        self.send(user.handle, self.name, 'group-enter', kval)

    def member_del(self, user, reason=None):
        if user not in self.users:
            raise Exception('Duplicate removal')

        self.users.remove(user)
        user.groups.remove(self)

        kval = defaultdict(list)
        if not reason:
            reason = ['']
        
        kval['reason'].append(reason)

        self.send(user.handle, self.name, 'group-exit', kval)

    def message(self, user, message):
        # TODO various ACL checks
        if user not in self.users:
            raise Exception('User not in group')

        kval = defaultdict(list)
        kval['message'].append(message)

        self.send(self.name, user.handle, 'message', kval, [user])

    def send(self, source, target, command, kval=None, filter=[]):
        for user in self.users:
            if user in filter:
                continue

            user.send(source, target, self.name, command, kval)

