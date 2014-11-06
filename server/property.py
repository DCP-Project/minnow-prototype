# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import enum
from time import time

class PropertyUserValues(enum.Enum):
    private = None
    wallops = None


class PropertyGroupValues(enum.Enum):
    private = None
    invite = str
    moderated = None
    topic = str


class Property:
    __slots__ = ['value', 'setter', 'time']

    def __init__(self, value, setter=None, time_=None):
        self.value = value
        self.setter = setter

        if time_ is None:
            time_ = round(time())

        self.time = time_


class PropertyUserList:
    def __init__(self):
        self.property = dict()

    def set(self, property, value=None):
        property = PropertyUserValues(property.casefold())

        if property.value != None:
            # Try to "cast" to correct type specified by entry
            value = property.value(value)
        else:
            value = True

        self.property[property] = value

    def remove(self, property):
        self.property.pop(PropertyUserValues(property.casefold()))

    def get(self, property):
        return self.property.get(PropertyUserValues(property.casefold()), None)


class PropertyGroupList:
    def __init__(self):
        self.property = dict()
    
    def set(self, property, value=None):
        property = PropertyGroupValues(property.casefold())

        if property.value != None:
            # Try to "cast" to correct type specified by entry
            value = property.value(value)
        else:
            value = True

        self.property[property] = value

    def remove(self, property):
        self.property.pop(PropertyGroupValues(property.casefold()))

    def get(self, property):
        return self.property.get(PropertyGroupValues(property.casefold()), None)
