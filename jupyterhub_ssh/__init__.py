import asyncssh
import asyncio
import logging
import websockets
import json
from yarl import URL
from functools import partial

from aiohttp import ClientSession


async def create_terminado(
        session: ClientSession,
        notebook_url: URL,
        token: str):
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


TOKEN = ''
NOTEBOOK_URL = 'https://datahub.berkeley.edu/user/yuvipanda/'


class MySSHServer(asyncssh.SSHServer):
    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        return username == password


async def handle_client(process):
    headers = {
        'Authorization': f'token {TOKEN}'
    }

    async with ClientSession(headers=headers) as client:
        ws_url = await create_terminado(client, URL(NOTEBOOK_URL), TOKEN)
        print(ws_url)

    async with websockets.connect(str(ws_url), extra_headers=headers) as ws:
        while not process.stdin.at_eof():
            try:
                data = await asyncio.wait_for(process.stdin.read(4096), 0.1)
                print('in', data)
                await ws.send(json.dumps(['stdin', data]))
            except asyncio.TimeoutError:
                pass
            except asyncssh.misc.TerminalSizeChanged:
                pass
            except asyncssh.misc.BreakReceived:
                pass

            try:
                in_data = json.loads(await asyncio.wait_for(ws.recv(), 0.1))
                print('stdout', in_data)
                if in_data[0] == 'stdout':
                    process.stdout.write(in_data[1])
                    await process.stdout.drain()
                elif in_data[0] == 'stderr':
                    stderr.write(in_data[1])
                    await process.stderr.drain()
            except asyncio.TimeoutError:
                pass

async def start_server():
    await asyncssh.listen(
        host='',
        port=8022,
        process_factory=handle_client,
        server_factory=MySSHServer,
        line_editor=False,
        server_host_keys=['ssh_host_key']
    )

logger = logging.getLogger('asyncssh')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
asyncio.get_event_loop().run_until_complete(start_server())
asyncio.get_event_loop().run_forever()
