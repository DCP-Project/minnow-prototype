# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import json

from collections import defaultdict
from itertools import islice, takewhile
from functools import reduce
from operator import concat

from server.errors import *

MAXFRAME = 1400
MAXTARGET = 48
MAXCOMMAND = 32


class BaseFrame:
    def __init__(self, source, target, command, kval):
        self.source = source
        self.target = target
        self.command = command
        self.kval = kval

    @classmethod
    def from_other(cls, other):
        return cls(other.source, other.target, other.command, other.kval)

    @staticmethod
    def _generic_len(source, target, command, kval):
        raise NotImplementedError()

    def __len__(self):
        return self._generic_len(self.source, self.target, self.command,
                                 self.kval)

    @staticmethod
    def fit(command, kval):
        """ Get the minimum overhead for a frame with a given set of keys """
        llen = self._generic_len(MAXTARGET, MAXTARGET, command, kval)
        return MAXFRAME - llen


class Frame(BaseFrame):
    terminator = b'\0\0'

    @staticmethod
    def get_next(iterator):
        return reduce(concat, takewhile(lambda c: c != '\0', iterator))

    @classmethod
    def parse(cls, text):
        if len(text) < 10:
            raise ParserIncompleteError('Incomplete frame')

        if text[-2:] == cls.terminator:
            text = text[:-2]

        # Grab the llen
        llen = int.from_bytes(text[:2], 'big')
        if llen > MAXFRAME:
            raise ParserSizeError('Frame is too large for the wire')

        llen -= 2

        if llen != len(text):
            raise ParserSizeError('Junk size received')

        try:
            # Grab our iterator for the frame
            text = text.decode('utf-8', 'replace')
        except Exception as e:
            raise ParserError('Couldn\'t decode text: ' + str(e)) from e

        frame_iter = islice(text, 3, llen)
        llen -= 3

        try:
            source = cls.get_next(frame_iter)
            target = cls.get_next(frame_iter)
            command = cls.get_next(frame_iter)
        except Exception as e:
            raise ParserError('Invalid opening header') from e

        llen -= len(source) + len(target) + len(command) + 3

        kval = defaultdict(list)
        try:
            kval = defaultdict(list)
            while llen > 0:
                key = cls.get_next(frame_iter)
                value = cls.get_next(frame_iter)

                llen -= len(key) + len(value) + 2

                kval[key].append(value)
        except Exception as e:
            raise ParserError('Invalid keys/values') from e

        return cls(source, target, command, kval)

    def __bytes__(self):
        if len(self) > MAXFRAME - 20:
            # Offset is to ensure it fits within JSON too
            raise ParserSizeError('Frame is too large')

        frame = [self.source, self.target, self.command]
        for k, v in self.kval.items():
            for v2 in v:
                frame.extend([k, v2])

        frame.append('\0')

        frame = '\0'.join(frame)

        # has to include the len of the short (2 bytes) + the sep
        llen = int.to_bytes(len(frame) + 3, 2, 'big')

        frame = llen + b'\0' + frame.encode('utf-8', 'replace')
        return frame

    @staticmethod
    def len_kv(kval):
        l = sum(sum((len(k)+len(v2)+2) for v2 in v) for k, v in kval.items())
        return l

    @staticmethod
    def _generic_len(source, target, command, kval):
        # We count the two byte short, and all nulls we know of now (including
        # the end and the known separators)
        llen = 3 + len(source) + 1 + len(target) + 1 + len(command) + 1 + 2

        if len(kval) > 0:
            llen += Frame.len_kv(kval) - 1

        return llen

    def __repr__(self):
        fmtstr = 'Frame(source={}, target={}, command={}, kval={})'
        return fmtstr.format(self.source, self.target, self.command, self.kval)


class JSONFrame(BaseFrame):
    terminator = b'\0'

    @classmethod
    def parse(cls, text):
        if not text.endswith(cls.terminator) or len(text) < 10:
            raise ParserIncompleteError('Incomplete frame')

        if len(text) < 20:
            raise ParserSizeError('Frame is too small')

        if len(text) > MAXFRAME:
            raise ParserSizeError('Frame is too large')

        text = text.decode('utf-8', 'replace')

        try:
            load = json.loads(text)
        except Exception as e:
            raise ParserSizeError(str(e)) from e

        try:
            header = load[0]

            source = header['source']
            target = header['target']
            command = header['command']
        except Exception as e:
            raise ParserInvalidError('Bad JSON frame header') from e

        try:
            kval = defaultdict(list, (load[1] if len(load) > 1 else {}))
            for key, val in kval.items():
                if not isinstance(val, list):
                    # Validate the values
                    raise ParserInvalidError('Value not a list')

                for val2 in val:
                    # Validate all values of the values
                    if not isinstance(val2, str):
                        raise ParserInvalidError('Value in list not a str')
        except Exception as e:
            raise ParserInvalidError('Bad JSON frame key/values') from e

        return cls(source, target, command, kval)

    def __bytes__(self):
        header = {
            'source': self.source,
            'target': self.target,
            'command': self.command
        }
        dump = (header, self.kval)

        frame = (json.dumps(dump, separators=(',', ':')) + '\0')
        if len(frame) > MAXFRAME:
            raise ParserSizeError('Frame is too big for the wire')

        frame = frame.encode('utf-8', 'ignore')
        return frame

    @staticmethod
    def len_kv(kval):
        if not kval:
            return 0

        l = 0
        for k, v in kval.items():
            # Each key: val pair introduces at least 6 bytes overhead
            l += 6 + len(k)

            # Each value adds at least 3 chars of overhead per item
            for v2 in v:
                l += 3 + len(v2)

            # Adjust for trailing comma
            l -= 1

        # Trailing comma
        l -= 1
        return l

    @staticmethod
    def _generic_len(source, target, command, kval):
        # 44 is the base length of a JSON frame minus keys/values
        # (however it does include quotes)
        baselen = 44 + len(source) + len(target) + len(command)
        baselen += JSONFrame.len_kv(kval)

        return baselen

    def __repr__(self):
        fmtstr = 'JSONFrame(source={}, target={}, command={}, kval={})'
        return fmtstr.format(self.source, self.target, self.command, self.kval)
