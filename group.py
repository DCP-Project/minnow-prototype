from collections import defaultdict
from user import DCPUser

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

    def member_del(self, user, reason=None, permanent=False):
        if user not in self.users:
            raise Exception('Duplicate removal')

        self.users.remove(user)
        user.groups.remove(self)

        kval = defaultdict(list)
        if not reason:
            reason = ['']
        
        kval['reason'].append(reason)

        if permanent:
            kval['quit'] = '*'

        self.send(user.handle, self.name, 'group-exit', kval)

    def message(self, source, message):
        # TODO various ACL checks
        if isinstance(source, DCPUser) and source not in self.users:
            self.server.error(source, 'message', 'You aren\'t in that group',
                              False)
            return

        kval = defaultdict(list)
        kval['body'] = message

        self.send(self.name, user.handle, 'message', kval, [source])

    def send(self, source, target, command, kval=None, filter=[]):
        for user in self.users:
            if user in filter:
                continue

            user.send(source, target, self.name, command, kval)

