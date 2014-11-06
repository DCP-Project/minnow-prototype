# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

from abc import ABCMeta, abstractmethod

class BaseCustomDict(dict, metaclass=ABCMeta):
    @abstractmethod
    def get_key(self, key):
        pass

    def __getitem__(self, key):
        return super().__getitem__(self.get_key(key))
    
    def __setitem__(self, key):
        return super().__setitem__(self.get_key(key))

    def __delitem__(self, key):
        return super().__delitem__(self.get_key(key))


class CaselessDict(BaseCustomDict):
    def get_key(self, key):
        return getattr(key, 'name', key).casefold()

