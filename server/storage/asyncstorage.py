# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import asyncio
import queue

from concurrent.futures import ThreadPoolExecutor
from functools import partial


# The pool of cached DCP storage objects
proto_storage_pool = queue.Queue()

# The executor itself
proto_storage_executor = ThreadPoolExecutor(32)


class AsyncStorage:
    def __init__(self, storeclass, args):
        self.storeclass = storeclass
        self.args = args

    def run_callback(self, method_call, *args):
        try:
            storage = proto_storage_pool.get_nowait()
        except queue.Empty:
            storage = self.storeclass(*self.args)

        try:
            method_call = getattr(storage, method_call)
            return method_call(*args)
        finally:
            # Place back into the pool
            proto_storage_pool.put(storage)

    def __getattr__(self, attr):
        loop = asyncio.get_event_loop()
        ret = partial(loop.run_in_executor, proto_storage_executor,
                      self.run_callback, attr)

        setattr(self, attr, ret)
        return ret
