# Config file for minnow
# (yes yes I know a python script isn't a config file)

import logging

### Server configuration

# Server name
servname = 'elizabethmyers.me.uk'

# Listen on this IP/port pair
listen = ('0.0.0.0', 7266)
listen_json = ('0.0.0.0', 7267)

# Server password
servpass = None

# Allow registrations
allow_register = True

# Path to Unix control socket
unix_path = 'data/control'

### Debug options

# Debug level (set to debug, please)
log_level = logging.DEBUG

### Performance options

# Maximum users to keep in the offline cache
# (Set to None for an unlimited amount)
max_cache = 1024
