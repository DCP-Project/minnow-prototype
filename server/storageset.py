# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.


import asyncio
import types


class StorageItem(types.SimpleNamespace):

    def set(self, *args):
        self.__init__(*args)


class StorageSet:

    """An object to hold DCP doodads (targets, users, properties, etc)"""

    KEY_ROW = 'name'
    eager = False
    check_db_fail = True

    def __init__(self, factory, storage=None):
        self.factory = factory
        self.storage = storage

        self._mapping = dict()

        if storage and self.eager:
            self.populate()

    @staticmethod
    def _get_key(key):
        key = getattr(key, 'name', key)
        if hasattr(key, 'lower'):
            key = key.lower()

        return key

    def populate(self):
        store = (yield from self._populate_db())
        if not store:
            return

        for item in store:
            # Prepare the args
            key = item[self.KEY_ROW]
            obj = self.factory(**{k: v for k, v in item.items()})
            self._mapping[key] = obj

    @asyncio.coroutine
    def _populate_db(self):
        ret = (yield from self.storage.get_all())
        return ret

    @asyncio.coroutine
    def add(self, key, *args, **kwargs):
        key = self._get_key(key)

        obj = self.factory(*args, **kwargs)
        self._mapping[key] = obj

        if self.storage:
            yield from self._add_db(key, *args, **kwargs)

        return obj

    @asyncio.coroutine
    def _add_db(self, key, *args, **kwargs):
        if self.storage:
            yield from self.storage.add(key, *args, **kwargs)

    @asyncio.coroutine
    def set(self, key, *args, **kwargs):
        key = self._get_key(key)

        item = self._mapping[key]
        for k, v in kwargs.items():
            setattr(item, k, v)

        if args:
            self._mapping[key].set(*args)

        yield from self._set_db(key, *args, **kwargs)

        return item

    @asyncio.coroutine
    def _set_db(self, key, *args, **kwargs):
        if self.storage:
            yield from self.storage.set(key, *args, **kwargs)

    @asyncio.coroutine
    def add_or_set(self, key, *args, **kwargs):
        self._get_key(key)

        if key in self._mapping:
            yield from self.set(key, *args, **kwargs)
        else:
            yield from self.add(key, *args, **kwargs)

    @asyncio.coroutine
    def get(self, key):
        key = self._get_key(key)
        obj = self._mapping.get(key)

        if not obj and self.check_db_fail:
            obj = (yield from self._get_db(key))
            if not obj:
                return

            self._mapping[key] = obj

        return obj

    @asyncio.coroutine
    def _get_db(self, key):
        if self.storage:
            ret = (yield from self.storage.get_one(key, *args, **kwargs))
            return ret

    @asyncio.coroutine
    def has(self, key):
        if self._get_key(key) in self._mapping:
            return True
        else:
            return (yield from self.get(key) is not None)

    @asyncio.coroutine
    def delete(self, key, *args, **kwargs):
        key = self._get_key(key)
        self._mapping.delete[key]

        yield from self._delete_db(key, *args, **kwargs)

    @asyncio.coroutine
    def _delete_db(self, key, *args, **kwargs):
        if self.storage:
            self.storage.delete(key, *args, **kwargs)

    def __contains__(self, key):
        return (yield from self.has(key))


class TargetStorageSet(StorageSet):

    """Storage set for targets"""

    def __init__(self, factory, storage=None, target=None):
        self.target = self._get_key(target)
        super().__init__(factory, storage)

    @asyncio.coroutine
    def _populate_db(self):
        ret = (yield from self.storage.get_all(self.target))
        return ret

    @asyncio.coroutine
    def _add_db(self, key, *args, **kwargs):
        if self.storage:
            yield from self.storage.add(self.target, key, *args, **kwargs)

    @asyncio.coroutine
    def _get_db(self, key):
        if self.storage:
            ret = (yield from self.storage.get_one(self.target, key))
            return ret
    
    @asyncio.coroutine
    def _set_db(self, key, *args, **kwargs):
        if self.storage:
            yield from self.storage.set(self.target, key, *args, **kwargs)

    def _delete_db(self, key, *args, **kwargs):
        if self.storage:
            yield from self.storage.delete(self.target, key, *args, **kwargs)
