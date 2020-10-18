import asyncssh
import asyncio
import logging
import websockets
import json
from yarl import URL
from contextlib import asynccontextmanager

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


HUB_URL = URL('https://datahub.berkeley.edu')

class MySSHServer(asyncssh.SSHServer):
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

    async def _handle_client(self, stdin, stdout, stderr):
        """
        Handle a single ssh client
        """
        headers = {
            'Authorization': f'token {self.token}'
        }

        async with ClientSession(headers=headers) as client:
            terminado = await Terminado.create(client, self.notebook_url, self.token)

        async with terminado.connect():
            # FIXME: Make this *actually* full duplex!
            # FIXME: This is terrible!
            while not stdin.at_eof():
                try:
                    data = await asyncio.wait_for(stdin.read(4096), 0.01)
                    await terminado.send_stdin(data)
                except asyncio.TimeoutError:
                    pass
                except asyncssh.misc.TerminalSizeChanged as e:
                    await terminado.set_size(e.height, e.width)
                except asyncssh.misc.BreakReceived:
                    pass

                try:
                    in_data = json.loads(await asyncio.wait_for(terminado.ws.recv(), 0.01))
                    if in_data[0] == 'stdout':
                        stdout.write(in_data[1])
                        await stdout.drain()
                    elif in_data[0] == 'stderr':
                        stderr.write(in_data[1])
                        await stderr.drain()
                except asyncio.TimeoutError:
                    pass

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
