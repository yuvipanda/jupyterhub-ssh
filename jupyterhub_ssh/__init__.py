import asyncssh
import asyncio
import logging
import websockets
import json
from yarl import URL
from contextlib import asynccontextmanager
from functools import partial

from aiohttp import ClientSession

class Terminado:
    @classmethod
    async def create(cls, session, notebook_url, token):
        notebook_secure = notebook_url.scheme == 'https'

        create_url = notebook_url / "api/terminals"
        async with session.post(create_url) as resp:
            data = await resp.json()
        terminal_name = data['name']
        socket_url = notebook_url / 'terminals/websocket' / terminal_name
        return cls(
            notebook_url=notebook_url,
            token=token,
            ws_url=socket_url.with_scheme('wss' if notebook_secure else 'ws')
        )

    def __init__(self, notebook_url, token, ws_url):
        self.notebook_url = notebook_url
        self.token = token
        self.ws_url = ws_url
        self.ws = None

    @asynccontextmanager
    async def connect(self):
        headers = {
            'Authorization': f'token {self.token}'
        }
        async with websockets.connect(str(self.ws_url), extra_headers=headers) as ws:
            self.ws = ws
            yield
        self.ws = None

    def send(self, data):
        """
        Send given data to terminado socket

        data should be a list of strings
        """
        return self.ws.send(json.dumps(data))

    def send_stdin(self, data):
        """
        Send data to stdin of terminado

        data should be a string
        """
        return self.send(['stdin', data])

    def set_size(self, rows, cols):
        """
        Set terminado's terminal cols / rows size
        """
        return self.send(['set_size', rows, cols])

    async def on_receive(self, on_receive):
        """
        Add callback for when data is received from terminado

        on_receive is called for each incoming message. Receives the JSON decoded
        message as only param.

        Returns when the connection has been closed
        """
        while True:
            try:
                data = await self.ws.recv()
            except websockets.exceptions.ConnectionClosedError as e:
                break
            await on_receive(json.loads(data))


HUB_URL = URL('https://datahub.berkeley.edu')

class MySSHServer(asyncssh.SSHServer):
    def connection_made(self, conn):
        self._conn = conn

    def password_auth_supported(self):
        return True

    async def validate_password(self, username, token):
        self.username = username
        self.token = token

        headers = {
            'Authorization': f'token {token}'
        }
        async with ClientSession(headers=headers) as session:
            async with session.get(HUB_URL / 'hub/api/users' / username) as resp:
                if resp.status != 200:
                    return False
                user = await resp.json()
                # URLs will have preceding slash, but yarl forbids those
                self.notebook_url = HUB_URL / user['servers']['']['url'][1:]
                return True

    async def _handle_ws_recv(self, stdout, data_packet):
        """
        Handle receiving a single data message from terminado.
        """
        kind, data = data_packet
        if kind == 'setup':
            # Signals we can get going now!
            return
        elif kind == 'change':
            # Sets terminal size, but let's ignore this for now
            return
        elif kind == 'disconnect':
            # Not exactly sure what to do here?
            return
        elif kind != 'stdout':
            raise ValueError(f'Unknown type {data[0]} received from terminado')
        stdout.write(data)
        await stdout.drain()


    async def _handle_stdin(self, stdin, terminado):
        """
        Handle receiving a single byte from stdin

        We aren't buffering anything rn, but maybe we should?
        """
        while not stdin.at_eof():
            try:
                data = await stdin.read(4096)
                await terminado.send_stdin(data)
            except asyncio.TimeoutError:
                pass
            except asyncssh.misc.TerminalSizeChanged as e:
                await terminado.set_size(e.height, e.width)
            except asyncssh.misc.BreakReceived:
                pass


    async def _handle_client(self, stdin, stdout, stderr):
        """
        Handle a single ssh client
        """
        headers = {
            'Authorization': f'token {self.token}'
        }

        async with ClientSession(headers=headers) as client:
            terminado = await Terminado.create(client, self.notebook_url, self.token)

        channel = stdin.channel

        async with terminado.connect():
            if channel.get_terminal_type():
                rows, cols = channel.get_terminal_size()[:2]
                await terminado.set_size(rows, rows)

            tasks = [
                asyncio.create_task(
                    terminado.on_receive(partial(self._handle_ws_recv, stdout))
                ),
                asyncio.create_task(self._handle_stdin(stdin, terminado))
            ]
            # Return when websocket or stdin reading tasks is done
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            # FIXME: If websocket died first, close stdin
            # FIXME: If stdin died first, close websocket.
            self._conn.close()
            for t in pending:
                t.cancel()

    def session_requested(self):
        return self._handle_client

async def start_server():
    await asyncssh.listen(
        host='',
        port=8022,
        server_factory=MySSHServer,
        line_editor=False,
        server_host_keys=['ssh_host_key']
    )

logger = logging.getLogger('asyncssh')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
asyncio.get_event_loop().run_until_complete(start_server())
asyncio.get_event_loop().run_forever()
