import websockets
import json
from contextlib import asynccontextmanager


class Terminado:
    def __init__(self, notebook_url, token, session):
        self.notebook_url = notebook_url
        self.token = token
        self.session = session

        self.headers = {
            'Authorization': f'token {self.token}'
        }

    async def __aenter__(self):
        """
        Create a terminal & connect to it
        """
        notebook_secure = self.notebook_url.scheme == 'https'

        create_url = self.notebook_url / "api/terminals"
        async with self.session.post(create_url, headers=self.headers) as resp:
            data = await resp.json()
        terminal_name = data['name']
        socket_url = self.notebook_url / 'terminals/websocket' / terminal_name
        ws_url = socket_url.with_scheme('wss' if notebook_secure else 'ws')

        self.ws = await websockets.connect(str(ws_url), extra_headers=self.headers)

        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Close the websocket to terminado

        FIXME: Also delete the terminal on the notebook server
        """
        await self.ws.close()

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
