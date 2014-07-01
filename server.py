import time
import asyncio
import user, group
import parser

# Flags for the annotations
UNREG = 1
SIGNON = 2

class DCPServer:
    def __init__(self, name, password='loldongs'):
        self.name = name
        self.password = password

        self.clients = dict()
        self.groups = dict()

server = DCPServer('test.org')

class DCPProto(asyncio.Protocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__buf = b''
        self.server = server
        self.user = None

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('connection from {}'.format(peername))
        self.transport = transport

    @staticmethod
    def _proto_name(target):
        if isinstance(target, (user.DCPUser, group.DCPGroup)):
            # XXX for now # is implicit with DCPGroup.
            # this is subject to change
            return target.name
        elif isinstance(target, DCPProto):
            return '=' + server.name
        elif target is None:
            return '*'
        else:
            return '&' + getattr(target, 'name', target)

    def send(self, source, target, command, kval=None):
        source = self._proto_name(source)
        target = self._proto_name(target)
        if kval is None: kval = dict()

        frame = parser.DCPFrame(source, target, command, kval)
        self.transport.write(bytes(frame))

    def error(self, reason, fatal=True):
        self.send(self, self.user, 'error', {'reason' : [reason]})

        if fatal:
            self.transport.close()

    def cmd_signon(self, line) -> UNREG:
        password = line.kval.get('password', ['*'])[0]
        if password != self.server.password:
            self.error('Invalid password')
            return

        del password

        name = line.kval.get('handle', [None])[0]
        if name is None:
            self.error('No handle')
            return

        if name.startswith(('=', '&' '!')):
            self.error('Invalid handle')
            return

        if name in self.server.clients:
            # TODO - burst all state to the user
            self.error('No multiple clients for the moment')
            return

        gecos = line.kval.get('gecos', [name])[0]
        options = line.kval.get('options', [])

        self.user = user.DCPUser(self, name, gecos, set(), options)
        self.server.clients[name] = self.user

        kval = {
            'name' : [self.server.name],
            'time' : [str(round(time.time()))],
            'options' : [],
        }
        self.send(self, self.user, 'signon', kval)

    def cmd_message(self, line) -> SIGNON:
        target = line.target
        if target == '*':
            self.error('No valid target', False)
            return

        # Lookup the target... no groups yet
        if target.startswith(('#', '=', '&')):
            self.error('Cannot message groups or servers yet, sorry', False)
            return

        if target not in self.server.clients:
            self.error('No such client', False)
            return

        # Get our target
        target = self.server.clients[target]

        # Get our message
        message = line.kval.get('body', [''])

        # Bam
        target.send(self.user, target, 'message', {'body' : message})

    def data_received(self, data):
        data = self.__buf + data

        if not data.endswith(b'\x00\x00'):
            data, sep, self.__buf = data.rpartition(b'\x00\x00')
            if sep:
                data += sep
            else:
                self.__buf = data
                return

        for line in parser.DCPFrame.parse(data):
            func = getattr(self, 'cmd_' + line.command, None)
            if func is None:
                self.error('No such command {}'.format(line.command), False)
                return

            req = func.__annotations__.get('return', SIGNON)
            if req & SIGNON:
                if not self.user:
                    self.error('You are not registered', False)
                    return
            elif req & UNREG:
                if self.user:
                    self.error('This command is only usable before ' \
                               'registration', False)
                    return

            try:
                func(line)
            except Exception as e:
                print('Uh oh! We got an error!')
                self.error('Internal server error')
                raise e
            
            print('Line recieved', repr(line))

loop = asyncio.get_event_loop()
coro = loop.create_server(DCPProto, '0.0.0.0', 7266)
aserver = loop.run_until_complete(coro)
print('serving on {}'.format(aserver.sockets[0].getsockname()))

try:
    loop.run_forever()
except KeyboardInterrupt:
    print("exit")
finally:
    aserver.close()
    loop.close()
