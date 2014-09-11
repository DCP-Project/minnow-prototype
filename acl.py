import enum
from time import time
from collections import defaultdict

class ACL:
    __slots__= ['setter', 'reason', 'time']

    def __init__(self, setter=None, reason=None, time_=None):
        self.setter = setter
        self.reason = reason
        if time_ is None:
            time_ = round(time())

        self.time = time_


class UserACLValues(enum.Enum):
    user_auspex     = 'user:auspex'
    user_register   = 'user:register'
    user_revoke     = 'user:revoke'
    user_grant      = 'user:grant'
    user_disconnect = 'user:disconnect'
    user_ban        = 'user:ban'

    group_auspex    = 'group:auspex'
    group_register  = 'group:register'
    group_override  = 'group:override'
    group_revoke    = 'group:revoke'
    group_ban       = 'group:ban'

    # Prohibition ACL's
    ban_banned      = 'ban:banned'
    ban_usermessage = 'ban:usermessage'


class GroupACLValues(enum.Enum):
    user_kick      = 'user:kick'
    user_ban       = 'user:ban'
    user_mute      = 'user:mute'
    user_voice     = 'user:voice'

    user_owner     = 'user:owner'
    user_admin     = 'user:admin'
    user_op        = 'user:op'

    group_topic    = 'group:topic'
    group_property = 'group:property'
    group_clear    = 'group:clear'

    # Prohibition ACL's
    ban_banned     = 'ban:banned'
    ban_mute       = 'ban:mute'


class UserACLSet:
    # TODO - move things like storage doodads and whatnot here.

    def __init__(self, acl_data=None):
        self.acl_map = dict()

        if not acl_data:
            return

        for acl in acl_data:
            self.add(acl['acl'], acl['setter'], acl['reason'],
                     acl['timestamp'])

    def __iter__(self):
        return iter(self.acl_map)

    def has_acl(self, acl):
        return acl in self.acl_map
    
    def get(self, acl):
        return self.acl_map.get(acl)

    def add(self, acl, setter=None, reason=None, time_=None):
        self.acl_map[acl] = ACL(setter, reason, time_)

    def delete(self, acl):
        self.acl_map.pop(acl, None)


class GroupACLSet:
    def __init__(self, acl_data=None):
        # XXX this will change someday
        self.acl_map = defaultdict(dict)

        if not acl_data:
            return

        for acl in acl_data:
            self.add(acl['user'], acl['acl'], acl['setter'], acl['reason'],
                     acl['timestamp'])

    def __iter__(self):
        for user, acl_ in self.acl_map.items():
            for acl in acl_:
                yield (user, acl)

    def has_acl(self, user, acl):
        user = getattr(user, 'name', user)
        return acl in self.acl_map[user]

    def get(self, user, acl):
        user = getattr(user, 'name', user)
        return self.acl_map.get(user)

    def add(self, user, acl, setter=None, reason=None, time_=None):
        user = getattr(user, 'name', user)
        self.acl_map[user][acl] = ACL(setter, reason, time_)

    def delete(self, user, acl):
        self.acl_map[user].pop(acl, None)

    def delete_all(self, user):
        self.acl_map.pop(user, None)

