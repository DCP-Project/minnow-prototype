#!/usr/bin/env python3

from os import chdir
from sys import argv, stderr
import shelve
from storage import UserStorage

if len(argv) < 3:
    print("Usage: {} username acl [...]".format(argv[0]), file=stderr)
    quit(1)

os.chdir('..')

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
            user.acl.remove(acl)
        else:
            print("Activating ACL {}".format(acl))
            user.acl.add(acl)

    db[username] = user

print("Success")
print("User will have to log in and out to complete the changes")
