# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

class DCPError(Exception):
    "The base DCP error class"
    pass


class ParserError(DCPError):
    "Base error for all parser errors"
    pass


class ParserIncompleteError(ParserError):
    "An incomplete frame was found"
    pass


class ParserSizeError(ParserError):
    "A frame was encountered of the wrong size"
    pass


class ParserValueError(ParserError):
    "A key:value pair was wrong"
    pass


class ParserInvalidError(ParserError):
    "A frame is invalid for some reason"
    pass


class MultipartError(ParserError):
    "A problem was found with multipart"
    pass


class MultipartKeyError(MultipartError):
    "A bad multipart key was found"
    pass

class MultipartOverflowError(MultipartError):
    "A multipart message overflowed"
    pass


class UserError(DCPError):
    "Base error for all user-related doodads"
    pass


class GroupError(DCPError):
    "Base error for all group-related doodads"
    pass


class GroupAdditionError(UserError, GroupError):
    "Couldn't add user to group"
    pass


class GroupRemovalError(UserError, GroupError):
    "Couldn't remove user from group"
    pass


class CommandError(DCPError):
    "Base error for command-related doodads"
    pass


class CommandNotImplementedError(CommandError, NotImplementedError):
    "Command is not implemented"
    pass


class RegisteredOnlyError(CommandNotImplementedError):
    "Command can only be executed by registered users"
    pass


class UnregisteredOnlyError(CommandNotImplementedError):
    "Command can only be executed by unregistered users"
    pass


class ACLError(DCPError):
    "Base error for ACL errors"
    pass


class CommandACLError(ACLError, CommandError):
    "Not enough permission to execute command"
    def __init__(self, acl, *args):
        self.acl = acl
        super().__init__(*args)


class ACLExistsError(ACLError):
    "ACL already exists"
    pass


class ACLDoesNotExistError(ACLError):
    "ACL does not exist"
    pass


class StorageError(DCPError):
    "Storage backend related error"
    pass


class StorageBackendNotFoundError(StorageError):
    "Could not find given storage backend"
    pass


class PropertyError(DCPError):
    "Base error for property errors"
    pass


class PropertyDoesNotExistError(PropertyError):
    "Property doesn't exist"
    pass


class PropertyInvalidError(PropertyError):
    "Property is invalid"
    pass


class PropertyValueError(PropertyError):
    "Property has a bad value"
    pass
