#!/usr/bin/env python3
# coding: utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import socket
import sys
import argparse

from pathlib import Path
basedir = Path(__file__).resolve().parent.parent
sys.path.append(str(basedir))

import settings

from server.parser import JSONFrame, MAXFRAME


def process_data(sock):
    data = b''
    while not (data and data.endswith(JSONFrame.terminator)):
        data += sock.recv(MAXFRAME * 4)

    data = data.split(JSONFrame.terminator)
    return [JSONFrame.parse(d + JSONFrame.terminator) for d in data if d]


parser = argparse.ArgumentParser(description='Modfiy a user\'s ACL\'s on the server')
parser.add_argument('--set', nargs='+', help="ACL's to grant to the handle")
parser.add_argument('--delete', nargs='+', help="ACL's to delete from the handle")
parser.add_argument('handle', help="Username to modify")

args = parser.parse_args()
if not (args.set or args.delete):
    print('Must have ACL\'s to set or del', file=sys.stderr)
    quit(1)

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
path = str(basedir.joinpath(settings.unix_path))
print('Connecting to', path)
sock.connect(path)

resp = []
if args.set:
    kwds = {
        'acl': args.set,
    }

    print(bytes(JSONFrame(args.handle, '*', 'acl-set', kwds)))
    sock.sendall(bytes(JSONFrame(args.handle, '*', 'acl-set', kwds)))
    resp.extend(process_data(sock))

if args.delete:
    kwds = {
        'acl': args.delete,
    }

    sock.writeall(bytes(JSONFrame(args.handle, '*', 'acl-del', kwds)))
    resp.extend(process_data(sock))

print('Response:', repr(resp))
