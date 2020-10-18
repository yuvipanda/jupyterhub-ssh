import websockets
import json
from contextlib import asynccontextmanager


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
                print("websocket done")
                break
            await on_receive(json.loads(data))
