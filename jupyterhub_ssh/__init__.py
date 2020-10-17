import asyncssh
import asyncio
import logging
import websockets
import json
from yarl import URL

from aiohttp import ClientSession


async def create_terminado(session: ClientSession, notebook_url: URL, token: str):
    """
    Create a Terminal, returning websocket path
    """
    notebook_secure = notebook_url.scheme == 'https'

    create_url = notebook_url / "api/terminals"
    async with session.post(create_url) as resp:
        data = await resp.json()
    terminal_name = data['name']
    socket_url = notebook_url / 'terminals/websocket' / terminal_name
    return socket_url.with_scheme('wss' if notebook_secure else 'ws')


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
            ws_url = await create_terminado(client, self.notebook_url, self.token)

        async with websockets.connect(str(ws_url), extra_headers=headers) as ws:
            # FIXME: Make this *actually* full duplex!
            # FIXME: This is terrible!
            while not stdin.at_eof():
                try:
                    data = await asyncio.wait_for(stdin.read(4096), 0.01)
                    await ws.send(json.dumps(['stdin', data]))
                except asyncio.TimeoutError:
                    pass
                except asyncssh.misc.TerminalSizeChanged:
                    pass
                except asyncssh.misc.BreakReceived:
                    pass

                try:
                    in_data = json.loads(await asyncio.wait_for(ws.recv(), 0.01))
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
