#!/usr/bin/env python3

import os
from sys import argv, stderr, path
import shelve

if len(argv) < 3:
    print("Usage: {} username acl [...]".format(argv[0]), file=stderr)
    quit(1)

if not os.path.exists('users.db') or os.path.exists('users.db.db'):
    os.chdir('..')

# The below doesn't work without this grr
path.append(os.getcwd())
import storage

username = argv[1]
acl_list = argv[2:]
with shelve.open('users.db') as db:
    if username not in db:
        print("User not found", file=stderr)
        quit(2)

    user = db[username]

    for acl in acl_list:
        acl = acl.lower()
        if acl in user.acl:
            print("Deactivating ACL {}".format(acl))
            del user.acl[acl]
        else:
            print("Activating ACL {}".format(acl))
            user.acl[acl] = (0, 'Activated from command line')

    db[username] = user

print("Success")
print("User will have to log in and out to complete the changes")
