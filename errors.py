class DCPError(Exception):
    pass


class ParserError(DCPError):
    pass


class ParserIncompleteError(ParserError):
    pass


class ParserSizeError(ParserError):
    pass


class ParserValueError(ParserError):
    pass


class ParserInvalidError(ParserError):
    pass


class MultipartError(ParserError):
    pass


class MultipartOverflowError(ParserError):
    pass


class UserError(DCPError):
    pass


class GroupError(DCPError):
    pass


class GroupAdditionError(GroupError):
    pass


class GroupRemovalError(GroupError):
    pass


class CommandError(Exception):
    pass


class CommandACLError(CommandError):
    def __init__(self, acl, *args):
        self.acl = acl
        super().__init__(*args)


class CommandNotImplementedError(CommandError, NotImplementedError):
    pass

