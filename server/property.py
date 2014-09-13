import enum

class UserPropertyValues(enum.Enum):
    private = ('private', None)
    wallops = ('wallops', None)
    banned  = ('banned',  int)


class GroupPropertyValues(enum.Enum):
    private = ('private', None)
    invite  = ('invite',  str)
    topic   = ('topic',   str)


class BaseProperty:
    __slots__ = ['options', 'option_map']

    def __init__(self, options):
        self.options = options

        self.option_map = dict()

    def __getitem__(self, option):
        if not hasattr(option, 'name'):
            option = self.options[option]

        return self.option_map[option.name]

    def __setitem__(self, option, item):
        if not hasattr(option, 'name'):
            option = self.options[option]

        name, type_ = option.value
        if type_ is not None:
            item = type_(item)

        self.option_map[option.name] = item

    def __delitem__(self, option):
        if not hasattr(option, 'name'):
            option = self.options[option]

        del self.option_map[option.name]

    def __iter__(self):
        return iter(self.option_map)

    def items(self):
        return iter(self.options.items())


class UserProperty(BaseProperty):
    __slots__ = BaseProperty.__slots__

    def __init__(self):
        return super().__init__(UserPropertyValues)


class GroupProperty(BaseProperty):
    __slots__ = BaseProperty.__slots__

    def __init__(self):
        return super().__init__(GroupPropertyValues)
