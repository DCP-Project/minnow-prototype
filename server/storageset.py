# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.


import types


class StorageItem(types.SimpleNamespace):

    def set(self, *args):
        self.__init__(*args)


class StorageSet:

    """An object to hold DCP doodads (targets, users, properties, etc)"""

    KEY_ROW = 'name'

    def __init__(self, factory, storage=None, target=None):
        self.factory = factory
        self.storage = storage
        self.target = self._get_key(target)

        assert (target if storage else True)

        self._mapping = dict()

        if storage:
            self.populate()

    @staticmethod
    def _get_key(key):
        key = getattr(key, 'name', key)
        if hasattr(key, 'lower'):
            key = key.lower()

        return key

    def populate(self):
        store = self.storage.get(self.target)
        if not store:
            return

        for item in store:
            # Prepare the args
            self.add(item[self.KEY_ROW], **item)

    def add(self, key, commit=False, *args, **kwargs):
        key = self._get_key(key)

        obj = self.factory(*args, **kwargs)
        self._mapping[key] = obj

        if self.storage and commit:
            self.storage.add(self.target, key, *args, **kwargs)

        return obj

    def set(self, key, *args, **kwargs):
        key = self._get_key(key)

        item = self._mapping[key]
        for k, v in kwargs.items():
            setattr(item, k, v)

        if args:
            self._mapping[key].set(*args)

        if self.storage:
            self.storage.set(self.target, key, *args, **kwargs)

        return item

    def add_or_set(self, key, *args, **kwargs):
        self._get_key(key)

        if key in self._mapping:
            return self.set(key, *args, **kwargs)
        else:
            return self.add(key, *args, **kwargs)

    def get(self, key):
        key = self._get_key(key)
        obj = self._mapping.get(key)

        if obj:
            return obj

    def has(self, key):
        return self._get_key(key) in self._mapping

    def delete(self, key, *args, **kwargs):
        key = self._get_key(key)
        self._mapping.delete[key]

        if self.storage:
            self.storage.delete(self.target, key, *args, **kwargs)

    def __contains__(self, key):
        key = self._get_key(key)
        return key in self._mapping
