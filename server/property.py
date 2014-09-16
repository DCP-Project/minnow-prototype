# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import enum
from time import time

class UserPropertyValues(enum.Enum):
    private = None
    wallops = None


class GroupPropertyValues(enum.Enum):
    private = None
    invite = str
    moderated = None
    #topic = str


class Property:
    __slots__ = ['value', 'setter', 'time_']

    def __init__(self, value, setter=None, time_=None):
        self.value = value
        self.setter = setter

        if time_ is None:
            time_ = round(time)

        self.time = time_


class BasePropertySet:
    __slots__ = ['server', 'prop_map']

    def __init__(self, server, prop_data=None):
        # NOTE - we use prop_data here separate instead of getting it ourselves
        # because __init__ being a coroutine is probably dodgy.
        self.server = server
        self.prop_map = dict()

        if not prop_data:
            return

        for property in prop_data:
            self._set_nocommit(property['property'], property['setter'],
                               property['timestamp'])

    def __iter__(self):
        return self.prop_map.items()

    def has_property(self, property):
        return property in self.prop_map

    def get(self, property):
        return self.prop_map.get(property)

    def _set_nocommit(self, property, value, setter=None, time_=None):
        self.prop_map[property] = Property(value, setter, time_)

    def set(self, property, value, setter=None):
        if not isinstance(property, str):
            assert len(property) = len(value)

            for i, p in enumerate(property):
                self.set(p, value[i], setter)

            return

        self._set_nocommit(property, value, setter)

    def delete(self, property):
        if not isinstance(property, str):
            for p in property:
                self.delete(a)

            return

        if property not in self.prop_map:
            raise PropertyDoesNotExistError('Property does not exist')

        del self.prop_map[property]


class UserPropertySet(BasePropertySet):
    __slots__ = BasePropertySet.__slots__ + ['user']

    def __init__(self, server, user, prop_data=None):
        super().__init__(server, prop_data)
        self.user = user.lower()

    def _set_nocommit(self, property, value, setter=None, time_=None):
        property = property.lower()

        if property not in UserPropertyValues:
            # Don't choke when the db sends us bad values
            return

        if not setter:
            setter = self.user

        typecast = UserPropertyValues[property]
        if typecast is not None:
            try:
                value = typecast(value)
            except Exception as e:
                raise PropertyValueError() from e

        super()._set_nocommit(property, value, setter, time_)

    def set(self, property, value, setter=None):
        property = property.lower()
        if property not in UserPropertyValues:
            raise PropertyInvalidError(property)

        setter = getattr(setter, 'name', setter)

        super().set(property, value, setter)

        if setter:
            setter = setter.lower()

        function = self.server.proto_store.set_property_user
        asyncio.async(function(self.user, property, value, setter))

    def delete(self, property):
        super().delete(property)
        function = self.server.proto_store.delete_property_user
        asyncio.async(function(self.user, property))


class GroupPropertySet(BasePropertySet):
    __slots__ = BasePropertySet.__slots__ + ['group']

    def __init__(self, server, group, prop_data=None):
        super().__init__(server, prop_data)
        self.group = group.lower()

    def _set_nocommit(self, property, value, setter=None, time_=None):
        property = property.lower()

        if property not in GroupPropertyValues:
            return

        typecast = GroupPropertyValues[property]
        if typecast is not None:
            try:
                value = typecast(value)
            except Exception as e:
                raise PropertyValueError() from e

        super()._set_nocommit(property, value, setter, time_)

    def set(self, property, value, setter=None):
        property = property.lower()
        if property not in GroupPropertyValues:
            raise PropertyInvalidError(property)

        setter = getattr(setter, 'name', setter)
        super().set(property, value, setter)

        if setter:
            setter = setter.lower()

        function = self.server.proto_store.set_property_group
        asyncio.async(function(self.group, property, value, setter))

    def delete(self, property):
        super().delete(property)
        function = self.server.proto_store.delete_property_group
        asyncio.async(function(self.group, property))
