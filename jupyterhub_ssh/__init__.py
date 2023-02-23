import asyncio
import logging
from functools import partial

import asyncssh
from aiohttp import ClientSession
from async_timeout import timeout
from traitlets import Any
from traitlets import Bool
from traitlets import Integer
from traitlets import Unicode
from traitlets import validate
from traitlets.config import Application
from yarl import URL

from .terminado import Terminado


class NotebookSSHServer(asyncssh.SSHServer):
    """
    A single SSH connection mapping to a notebook server on a JupyterHub
    """

    def __init__(self, app, *args, **kwargs):
        self.app = app
        self.fail_banner_sent = False
        super().__init__(*args, **kwargs)

    def connection_made(self, conn):
        """
        Connection has been successfully established
        """
        self._conn = conn

    def password_auth_supported(self):
        return True

    async def get_user_server_url(self, session, username):
        """
        Return user's server url if it is running.

        Else return None
        """
        async with session.get(self.app.hub_url / "hub/api/users" / username) as resp:
            if resp.status != 200:
                return None
            user = await resp.json()
            print(user)
            # URLs will have preceding slash, but yarl forbids those
            server = user.get("servers", {}).get("", {})
            if server.get("ready", False):
                return self.app.hub_url / user["servers"][""]["url"][1:]
            else:
                return None

    async def start_user_server(self, session, username):
        """ """
        # REST API reference:       https://jupyterhub.readthedocs.io/en/stable/_static/rest-api/index.html#operation--users--name--server-post
        # REST API implementation:  https://github.com/jupyterhub/jupyterhub/blob/187fe911edce06eb067f736eaf4cc9ea52e69e08/jupyterhub/apihandlers/users.py#L451-L497
        create_url = self.app.hub_url / "hub/api/users" / username / "server"

        async with session.post(create_url) as resp:
            if resp.status == 201 or resp.status == 400:
                # FIXME: code 400 can mean "pending stop" or "already running",
                #        but we assume it means that the server is already
                #        running.

                # Server started quickly
                # We manually generate this, even though it's *bad*
                # Mostly because when the server is already running, JupyterHub
                # doesn't respond with the whole model!
                return self.app.hub_url / "user" / username
            elif resp.status == 202:
                # Server start has been requested, now and potentially earlier,
                # but hasn't started quickly and is pending spawn.
                # We check for a while, reporting progress to user - until we're
                # done
                try:
                    async with timeout(self.app.start_timeout):
                        notebook_url = None
                        self._conn.send_auth_banner("Starting your server...")
                        while notebook_url is None:
                            # FIXME: Exponential backoff + make this configurable
                            await asyncio.sleep(0.5)
                            notebook_url = await self.get_user_server_url(
                                session, username
                            )
                            self._conn.send_auth_banner(".")
                        self._conn.send_auth_banner("done!\n")
                        return notebook_url
                except asyncio.TimeoutError:
                    # Server didn't start on time!
                    self._conn.send_auth_banner("failed to start server on time!\n")
                    return None
            elif resp.status == 403:
                # Token is wrong!
                return None
            else:
                # FIXME: Handle other cases that pop up
                resp.raise_for_status()

    async def validate_password(self, username, token):
        self.username = username
        self.token = token

        headers = {"Authorization": f"token {token}"}
        async with ClientSession(headers=headers) as session:
            notebook_url = await self.start_user_server(session, username)
            if notebook_url is None:
                if self.app.banner_auth_fail and not self.fail_banner_sent:
                    self.fail_banner_sent = True
                    self._conn.send_auth_banner(self.app.banner_auth_fail)
                return False
            else:
                self.notebook_url = notebook_url
                return True

    async def _handle_ws_recv(self, stdout, data_packet):
        """
        Handle receiving a single data message from terminado.
        """
        kind, data = data_packet
        if kind == "setup":
            # Signals we can get going now!
            return
        elif kind == "change":
            # Sets terminal size, but let's ignore this for now
            return
        elif kind == "disconnect":
            # Not exactly sure what to do here?
            return
        elif kind != "stdout":
            raise ValueError(f"Unknown type {data[0]} received from terminado")
        stdout.write(data)
        await stdout.drain()

    async def _handle_stdin(self, stdin, terminado):
        """
        Handle receiving a single byte from stdin

        We aren't buffering anything rn, but maybe we should?
        """
        while not stdin.at_eof():
            try:
                # Return *upto* 4096 bytes from the stdin buffer
                # Returns pretty immediately - doesn't *wait* for 4096 bytes
                # to be present in the buffer.
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
        async with ClientSession() as client, Terminado(
            self.notebook_url, self.token, client
        ) as terminado:

            # If a pty has been asked for, we tell terminado what the pty's current size is
            # Otherwise, terminado uses default size of 80x22
            channel = stdin.channel
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
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )

            # At least one of the pipes is done.
            # Close the ssh connection explicitly
            self._conn.close()

            # Explicitly cancel the other tasks currently pending
            # FIXME: I don't know if this actually does anything?
            for t in pending:
                t.cancel()

    def session_requested(self):
        return self._handle_client


class JupyterHubSSH(Application):
    config_file = Unicode(
        "jupyterhub_ssh_config.py",
        help="""
        Config file to load JupyterHub SSH config from
        """,
        config=True,
    )

    port = Integer(
        8022,
        help="""
        Port the ssh server listens on
        """,
        config=True,
    )

    debug = Bool(
        True,
        help="""
        Turn on debugg logging
        """,
        config=True,
    )

    hub_url = Any(
        "",
        help="""
        URL of JupyterHub's proxy to connect to.

        jupyterhub-ssh needs to be able to connect to both the JupyterHub API
        (/hub/api) and to the users' servers (/user/<username>) via HTTP or
        HTTPS. This URL doesn't have to be the public URL though as the URL is
        only be used by jupyterhub-ssh itself.

        *Must* be set.

        Examples:

        - If jupyterhub-ssh is deployed in the same Kubernetes cluster and
          namespace as the official JupyterHub Helm chart, you can use
          `http://proxy-public` or `http://proxy-http:8000` depending on
          how the JupyterHub Helm chart is configured. Use
          `http://proxy-http:8000` if the JupyterHub Helm chart has been
          configured with both `proxy.https.enabled=true` and
          `proxy.https.type=letsencrypt`, otherwise use `http://proxy-public`.

        - If jupyterhub-ssh can't access JupyterHub's proxy via local network or
          you don't trust the local network to be secure, use a public URL with
          HTTPS such as `https://my-hub-url.com`.
        """,
        config=True,
    )

    @validate("hub_url")
    def _hub_url_cast_string_to_yarl_url(self, proposal):
        if isinstance(proposal.value, str):
            return URL(proposal.value)
        elif isinstance(proposal.value, URL):
            return proposal.value
        else:
            raise ValueError("hub_url must either be a string or a yarl.URL")

    host_key_path = Unicode(
        "",
        help="""
        Path to host's private SSH Key.

        *Must* be set.
        """,
        config=True,
    )

    start_timeout = Integer(
        30,
        help="""
        Timeout in seconds to wait for a server to start before before closing
        the SSH connection.
        """,
        config=True,
    )

    banner_auth_fail = Unicode(
        "",
        help="""
        Text to be presented to client when authentication fails the first time.
        Can be used to point the user to documentation.
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

        asyncssh_logger = logging.getLogger("asyncssh")
        asyncssh_logger.propagate = True
        asyncssh_logger.parent = self.log
        asyncssh_logger.setLevel(self.log.level)

    def initialize(self, *args, **kwargs):
        super().initialize(*args, **kwargs)
        self.load_config_file(self.config_file)
        self.init_logging()

    async def start_server(self):
        await asyncssh.listen(
            host="",
            port=self.port,
            server_factory=partial(NotebookSSHServer, self),
            line_editor=False,
            password_auth=True,
            server_host_keys=[self.host_key_path],
            agent_forwarding=False,  # The cause of so much pain! Let's not allow this by default
            keepalive_interval=30,  # FIXME: Make this configurable
        )


def main():
    app = JupyterHubSSH()
    app.initialize()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.start_server())
    loop.run_forever()
