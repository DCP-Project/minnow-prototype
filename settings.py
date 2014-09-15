""" Config system for minnow """

from configparser import ConfigParser
import logging
import os
import socket
import sys

def _determine_prefix():
    """Determine the prefix directory for configuration files."""
    prefix = sys.prefix

    if prefix == '/usr':
        prefix = ''

    return prefix

class ImproperConfigurationError(Exception):
    """Raised when a (very) invalid configuration is provided."""
    pass

class MinnowSettings(object):
    """Settings object, basically a ConfigParser with our own defaults."""
    def __init__(self, path):
        """Initialise the settings object, loading settings from the file at
        'path'."""
        self._config = ConfigParser()
        self._config.read(path)

        if not self._config.has_section('server'):
            raise ImproperConfigurationError("No server options set!")

        # server settings
        self.servname = self._config['server'].get('servname', socket.getfqdn())

        ip = self._config['server'].get('listen_ip', '0.0.0.0')
        port = int(self._config['server'].get('listen_port', '7266'))
        self.listen = (ip, port)

        want_json = self._config['server'].getboolean('enable_json', True)
        if want_json:
            jip = self._config['server'].get('json_listen_ip', '0.0.0.0')
            jport = int(self._config['server'].get('json_listen_port', '7267'))
            self.listen_json = (jip, jport)
        else:
            self.listen_json = ('127.0.0.1', 7267)  # XXX TODO handle better

        self.servpass = self._config['server'].get('password', None)
        self.allow_register = self._config['server'].getboolean('enable_registrations', True)
        self.unix_path = self._config['server'].get('ipc_socket_path', 'data/control')

        self.cert_file_path = self._config['server'].get('cert_file', 'cert.pem')

        # storage settings
        provider_name = self._config['storage'].get('backend', 'sqlite')
        module = __import__('server.storage', globals(), locals(), [provider_name])
        self.store_backend = getattr(module, provider_name).backend.ProtocolStorage
        self.store_backend_args = ('data/store.db',)  # XXX TODO bad

        # debug settings
        level = self._config['logging'].get('level', 'DEBUG').upper()
        self.log_level = getattr(logging, level)

        # performance settings
        cache = self._config['performance'].get('max_cache', '1024')
        if cache.lower()[:2] == 'no':
            self.max_cache = None
        else:
            self.max_cache = int(cache)

cfg_path = os.path.join(_determine_prefix(), '/etc/minnow/minnow.conf')
sys.modules[__name__] = MinnowSettings([cfg_path, 'minnow.conf'])
