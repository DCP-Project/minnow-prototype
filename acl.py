import enum

class ACL:
    __slots__= ['time', 'reason']

    def __init__(self, time=0, reason=None):
        self.time = time
        self.reason = reason

    def modify(self, time=0, reason=None):
        self.time = time
        self.reason = reason


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


class BaseACL:
    def __init__(self, acls):
        self.acls = acls

        self.acl_map = dict()

    def __setitem__(self, acl, item):
        if not hasattr(acl, 'name'):
            acl = self.acls(acl)

        if acl in self.acl_map:
            self.acl_map[acl.name].modify(*item)
        else:
            self.acl_map[acl.name] = ACL(*item)

    def __getitem__(self, acl):
        if not hasattr(acl, 'name'):
            acl = self.acls(acl)

        item = self.acl_map[acl.name]
        return (item.time, item.reason)

    def __delitem__(self, acl):
        if not hasattr(acl, 'name'):
            acl = self.acls(acl)

        del self.acl_map[acl.name]

    def __contains__(self, acl):
        if not hasattr(acl, 'name'):
            acl = self.acls(acl)

        return acl.name in self.acl_map

    def __iter__(self):
        return iter(self.acl_map)

    def items(self):
        return iter((acl, item.time, item.reason) for acl, item in
                    self.acl_map.items())


class UserACL(BaseACL):
    __slots__ = ['acls', 'acl_map']

    def __init__(self):
        super().__init__(UserACLValues)


class GroupACL(BaseACL):
    __slots__ = ['acls', 'acl_map']

    def __init__(self):
        super().__init__(GroupACLValues)

