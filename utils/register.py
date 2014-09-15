#!/usr/bin/env python3
# coding: utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

import socket
import sys
import argparse
import getpass

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


parser = argparse.ArgumentParser(description='Register a handle on the server')
parser.add_argument('--gecos', default="Minnow User", help="User GECOS to use")
parser.add_argument('--password', help="User password (default: prompt)")
parser.add_argument('--acl', action='append', nargs='+', help="ACL's to use for the handle")
parser.add_argument('handle', help="Username of the new handle to add")

args = parser.parse_args()
if args.password is None:
    args.password = getpass.getpass()

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
path = str(basedir.joinpath(settings.unix_path))
print('Connecting to', path)
sock.connect(path)

kwds = {
    'handle': [args.handle],
    'password': [args.password],
    'gecos': [args.gecos],
}

sock.sendall(bytes(JSONFrame(args.handle, '*', 'register', kwds)))
resp = process_data(sock)

if args.acl:
    kwds = {
        'acl': args.acl,
    }

    sock.writeall(bytes(JSONFrame(args.handle, '*', 'acl-set', kwds)))
    resp.extend(process_data(sock))

print('Response:', repr(resp))
