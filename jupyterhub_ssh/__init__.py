import asyncssh
import asyncio
import logging
from yarl import URL
from functools import partial
from traitlets.config import Application
from traitlets import Integer, Unicode, Bool

from aiohttp import ClientSession

from .terminado import Terminado


HUB_URL = URL('https://datahub.berkeley.edu')

class NotebookSSHServer(asyncssh.SSHServer):
    """
    A single SSH connection mapping to a notebook server on a JupyterHub
    """
    def connection_made(self, conn):
        """
        Connection has been successfully established
        """
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
            except asyncssh.misc.TerminalSizeChanged as e:
                await terminado.set_size(e.height, e.width)
            except asyncssh.misc.BreakReceived:
                pass


    async def _handle_client(self, stdin, stdout, stderr):
        """
        Handle data transfer once session has been fully established.
        """
        headers = {
            'Authorization': f'token {self.token}'
        }

        async with ClientSession(headers=headers) as client:
            terminado = await Terminado.create(client, self.notebook_url, self.token)

        channel = stdin.channel

        async with terminado.connect():
            # If a pty has been asked for, we tell terminado what the pty's current size is
            # Otherwise, terminado uses default size of 80x22
            if channel.get_terminal_type():
                rows, cols = channel.get_terminal_size()[:2]
                await terminado.set_size(rows, rows)

            # We run two tasks concurrently
            #
            # terminado's stdout -> ssh stdout
            # ssh stdin -> terminado's stdin
            #
            # Terminado doesn't seem to separate out stderr, so we leave it alone
            #
            # When either of these tasks exit, we want to:
            # 1. Clean up the other task
            # 2. (Ideally) close the terminal opened by terminado on the notebook server
            # 3. Close the ssh connection
            #
            # We don't do all of these yet in a way that I can be satisfied with.

           
            # Pipe stdout from terminado to ssh
            ws_to_stdout = asyncio.create_task(
                terminado.on_receive(partial(self._handle_ws_recv, stdout))
            )
            #
            # Pipe stdin from ssh to terminado
            stdin_to_ws = asyncio.create_task(self._handle_stdin(stdin, terminado))

            tasks = [ws_to_stdout, stdin_to_ws]
           
            # Wait for either pipe to be done
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            # At least one of the pipes is done.
            # Close the ssh connection explicitly
            self._conn.close()

            # Explicitly cancel the other tasks currently pending
            # FIXME: I don't know if this actually does anything?
            for t in pending:
                t.cancel()

    def session_requested(self):
        return self._handle_client


class JupyterHubSSHApp(Application):
    port = Integer(
        8022,
        help="""
        Port the ssh server listens on
        """,
        config=True
    )

    debug = Bool(
        True,
        help="""
        Turn on debugg logging
        """,
        config=True
    )

    def init_logging(self):
        """
        Make traitlets & asyncssh logging work properly

        self.log is managed by traitlets, while the logger named
        asyncssh is managed by asyncssh. We want the debug flag to
        control debug logs everywhere, so we wire 'em together here.

        """
        self.log.setLevel(logging.DEBUG if self.debug else logging.INFO)
        # This propagates traitlet logs to root logger - somehow,
        # no logs were coming out otherwise
        self.log.propagate = True

        asyncssh_logger = logging.getLogger('asyncssh')
        asyncssh_logger.propagate = True
        asyncssh_logger.parent = self.log
        asyncssh_logger.setLevel(self.log.level)

    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        self.init_logging()

    async def start_server(self):
        await asyncssh.listen(
            host='',
            port=self.port,
            server_factory=NotebookSSHServer,
            line_editor=False,
            password_auth=True,
            server_host_keys=['ssh_host_key']
        )

def main():
    app = JupyterHubSSHApp()
    app.initialize()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.start_server())
    loop.run_forever()
