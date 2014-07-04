import json

from collections import defaultdict
from itertools import islice

from errors import *

MAXFRAME = 1370

class BaseFrame:
    def __init__(self, source, target, command, kval):
        self.source = source
        self.target = target
        self.command = command
        self.kval = kval

class Frame(BaseFrame):
    terminator = b'\0\0'

    @classmethod
    def parse(cls, text):
        lines = text.split(cls.terminator)
        if lines[-1] != b'':
            raise ParserIncompleteError('Incomplete frame')

        del lines[-1]

        retlines = []
        for line in lines:
            if len(line) < 10:
                raise ParserSizeError('Frame is too small')

            # Grab the llen
            llen = int.from_bytes(line[:2], 'big')
            if llen > MAXFRAME:
                raise ParserSizeError('Frame is too large')

            # Tokenise
            line = line[3:].split(b'\0')
            if line[-1] == b'':
                del line[-1]

            if len(line) < 3:
                raise ParserInvalidError('Invalid DCP frame')

            source = line[0].decode('utf-8', 'replace').lower()
            target = line[1].decode('utf-8', 'replace').lower()
            command = line[2].decode('utf-8', 'replace').lower()

            # Generate the key/val portion
            kval = defaultdict(list)

            if len(line) > 3:
                if (len(line) - 3) % 2:
                    # Pad if we have too few items
                    line.append(b'*')

                # This part might be a bit weird for a few...
                # We make a slice of line from the third position to the end,
                # then we duplicate the *same* iterator (same reference and all)
                # and feed it to zip, which will then output keys and values
                # sequentially one by one.
                i = [islice(iter(line), 3, None)] * 2
                for k, v in zip(*i):
                    # All keys are lowercase
                    k = k.decode('utf-8', 'replace').lower()
                    v = v.decode('utf-8', 'replace')
                    if v in kval[k]:
                        raise ParserValueError('Duplicate value not allowed')

                    kval[k].append(v)

            retlines.append(cls(source, target, command, kval))

        return retlines

    def __bytes__(self):
        line = [self.source, self.target, self.command]
        for k, v in self.kval.items():
            for v2 in v:
                line.extend([k, v2])

        line.append('\0')

        line = '\0'.join(line)

        # has to include the len of the short (2 bytes) + the sep
        llen = len(line) + 3
        if llen > MAXFRAME:
            raise ParserSizeError('Frame is too large')

        llen = int.to_bytes(llen, 2, 'big')

        line = llen + b'\0' + line.encode('utf-8', 'replace')
        return line

    def __len__(self):
        # We count the two byte short, and all nulls we know of now (including
        # the end and the known separators)
        llen = (3 + len(self.source) + 1 + len(self.target) + 1 +
                len(self.command) + 1 + 2)

        for k, v in self.kval.items():
            for v2 in v:
                # key + val + seps
                llen += len(k) + 1 + len(v2) + 1

        if len(self.kval) > 0:
            # We wind up with one too many from above, whoops
            llen -= 1

        return llen

    def __repr__(self):
        fmtstr = 'Frame(source={}, target={}, command={}, kval={})'
        return fmtstr.format(self.source, self.target, self.command, self.kval)


class JSONFrame(BaseFrame):
    terminator = b'\0'

    @classmethod
    def parse(cls, text):
        lines = text.split(cls.terminator)
        if lines[-1] != b'':
            raise ParserIncompleteError('Incomplete frame')

        del lines[-1]

        retlines = []
        for line in lines:
            if len(line) < 10:
                raise ParserSizeError('Frame is too small')

            # XXX there is a disparity between JSON and our frames...
            # I'm not sure how to reconcile it
            if len(line) > MAXFRAME + 20:
                raise ParserSizeError('Frame is too large')

            line = line.decode('utf-8', 'replace')

            try:
                load = json.loads(line)
            except Exception as e:
                raise ParserSizeError(str(e))

            try:
                header = load[0]

                source = header['source']
                target = header['target']
                command = header['command']
            except Exception as e:
                raise ParserInvalidError('Bad JSON frame header')

            try:
                kval = defaultdict(list, (load[1] if len(load) > 1 else {}))
                for key, val in kval:
                    if not isinstance(val, list):
                        # Validate the values
                        raise ParserInvalidError('Bad value')

                    for val2 in val:
                        # Validate all values of the values
                        if not isinstance(val, str):
                            raise ParserInvalidError('Bad value')
            except Exception as e:
                raise ParserInvalidError('Bad JSON frame key/values')

            retlines.append(cls(source, target, command, kval))

        return retlines

    def __bytes__(self):
        header = {
            'source' : self.source,
            'target' : self.target,
            'command' : self.command
        }
        dump = (header, self.kval)

        return (json.dumps(dump) + '\0').encode('utf-8', 'ignore')

    def __len__(self):
        return len(bytes(self))

    def __repr__(self):
        fmtstr = 'JSONFrame(source={}, target={}, command={}, kval={})'
        return fmtstr.format(self.source, self.target, self.command, self.kval)
