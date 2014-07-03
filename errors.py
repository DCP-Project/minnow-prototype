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


class UserError(DCPError):
    pass


class GroupError(DCPError):
    pass


class GroupAdditionError(GroupError):
    pass


class GroupRemovalError(GroupError):
    pass

