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
All configuration is done in the `config.py` file. Just edit it to taste.

The SSL certificate is stored in `cert.pem`. At the moment, this is
hard-coded.

The motd is stored in `motd.txt`. All lines will be truncated at 200 characters
for sanity reasons.

## Development
See the [TODO](https://github.com/DCP-Project/minnow-prototype/TODO.md) for 
details.
