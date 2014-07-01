import time
import asyncio
from user import DCPUser
from group import DCPGroup
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
        self.protos = dict() # XXX

    def process(self, proto, data):
        # Turn a protocol into a user
        client = self.protos.get(proto, None)

        for line in parser.DCPFrame.parse(data):
            func = getattr(self, 'cmd_' + line.command, None)
            if func is None:
                proto.error('No such command {}'.format(line.command), False)
                return

            req = func.__annotations__.get('return', SIGNON)
            if req & SIGNON:
                if not client:
                    proto.error('You are not registered', False)
                    return

                proto_or_user = client
            elif req & UNREG:
                if client:
                    proto.error('This command is only usable before ' \
                               'registration', False)
                    return

                proto_or_user = proto

            try:
                # XXX not sure I like this proto_or_user hack
                func(proto_or_user, line)
            except Exception as e:
                print('Uh oh! We got an error!')
                proto.error('Internal server error')
                raise e
            
            print('Line recieved', repr(line))

    def cmd_signon(self, proto, line) -> UNREG:
        password = line.kval.get('password', ['*'])[0]
        if password != self.password:
            proto.error('Invalid password')
            return

        del password

        name = line.kval.get('handle', [None])[0]
        if name is None:
            proto.error('No handle')
            return

        if name.startswith(('=', '&' '!')):
            proto.error('Invalid handle')
            return

        if name in self.clients:
            # TODO - burst all state to the user
            proto.error('No multiple clients for the moment')
            return

        gecos = line.kval.get('gecos', [name])[0]
        options = line.kval.get('options', [])

        user = DCPUser(proto, name, gecos, set(), options)
        self.protos[proto] = self.clients[name] = user

        kval = {
            'name' : [self.name],
            'time' : [str(round(time.time()))],
            'options' : [],
        }
        proto.send(self, user, 'signon', kval)

    def cmd_message(self, user, line) -> SIGNON:
        proto = user.proto
        target = line.target
        if target == '*':
            proto.error('No valid target', False)
            return

        # Lookup the target... no groups yet
        if target.startswith(('#', '=', '&')):
            proto.error('Cannot message groups or servers yet, sorry', False)
            return

        if target not in self.clients:
            proto.error('No such client', False)
            return

        # Get our target
        target = self.clients[target]

        # Get our message
        message = line.kval.get('body', [''])

        # Bam
        target.send(user, target, 'message', {'body' : message})

server = DCPServer('test.org')

class DCPProto(asyncio.Protocol):
    """ This is the asyncio connection stuff...

    Everything should just call back to the main server/client stuff here.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__buf = b''
        
        # Global state
        self.server = server

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('connection from {}'.format(peername))
        self.transport = transport

    def connection_lost(self, exc):
        peername = self.transport.get_extra_info('peername')
        print('connection lost from {} (reason {})'.format(peername, exc))

        client = self.server.protos.get(self, None)
        if client is None:
            return

        del self.server.protos[self]
        del self.server.clients[client.name]

        # TODO:
        # This is where we'd tell all the clients groups they've gone...

    def data_received(self, data):
        data = self.__buf + data

        if not data.endswith(b'\x00\x00'):
            data, sep, self.__buf = data.rpartition(b'\x00\x00')
            if sep:
                data += sep
            else:
                self.__buf = data
                return

        server.process(self, data)

    @staticmethod
    def _proto_name(target):
        if isinstance(target, (DCPUser, DCPGroup)):
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
        target = self.server.protos.get(self, None)
        self.send(self, target, 'error', {'reason' : [reason]})

        if fatal:
            self.transport.close()

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
