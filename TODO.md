Things that need to get done:

# Critical (unacceptable bugs/ommissions for production DCP)

The order of these doesn't matter.

## Protocol
- [ ] Rosters
- [ ] Working properties
- [ ] Global messaging
- [ ] Ability to change username
- [ ] Nicknames (linked to usernames)
- [ ] Multipart recieving (remember a len limit!)
- [ ] Bans of all types
- [ ] ACL checking
- [ ] Working multisession support

## Configuration/settings
- [ ] IPC utils over the Unix socket
- [ ] A **real** config system that isn't a Python file

## Storage
- [ ] PostgreSQL storage backend

## Other
- [ ] More protocol documentation
- [ ] More warnings/robustness
- [ ] Make this piece of shit faster

# Important (acceptable admissions for production DCP, but should be resolved)

## Protocol
- [ ] Make multipart work better
- [ ] Avatars
- [ ] Moods
- [ ] Statuses
- [ ] Metadata
- [ ] s2s operation

# Unimportant/maybe (some of these may never happen in DCP)

## Protocol
- [ ] Optional operation over SCTP sockets
- [ ] Possible change in the way groups/users/servers/remotes are distinguished
- [x] WebSocket transport. That was greasy. ¬_¬
- [ ] Maybe try JSON out a bit more
- [ ] Maybe a BSON transport?
- [ ] REALLY COOL! An IRC transport! Both client and TS6 would be amazing. 

## Configuration/settings
- [ ] Runtime module reloading
- [ ] Reduce state in server class to bare minimum, to allow reloading
- [ ] Make modules keep state they require

## Storage
- [ ] MariaDB storage backend
- [ ] Maybe a shelve backend again?

## Other
- [ ] Reimplement pieces in C for speed
