# Minnow - the prototype DCP server

## Introduction
This is a server for the Domain Chat Protocol (DCP).

The spec is actively being developed, as is this server, Minnow, and the
client, [Gilligan](https://github.com/DCP-Project/gilligan-prototype).

## Requirements
* Python 3.4 or above. It wouldn't be hard to retarget everything for Python
3.3 though. Python 3.2 is right out due to the addition of `yield from` in 3.3
(so asyncio won't work).
* A working SSL module
* All clients must speak TLS 1.2 atm (this raises the bar on purpose)

## Configuration
Minnow searches /etc/minnow and the current directory for `minnow.conf`.
Use the provided `minnow.conf.dist` as a starting point.

The motd is stored in `motd.txt`. All lines will be truncated at 200 characters
for sanity reasons.

## Development
See the [STATUS](https://github.com/DCP-Project/minnow-prototype/blob/master/status.md)
for details.

You can find us at irc.interlinked.me #dcp for the moment, ironically.

## Bugs
**Do not file bugs on DCP or Gilligan.** The server is nowhere near completion,
and therefore neither is the client. You can point out little things that
should be working and aren't to us on IRC.
