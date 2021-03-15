from aiohttp import ClientSession
import os
import pytest
from yarl import URL
import sys

from notebook.tests.launchnotebook import NotebookTestBase

from ..terminado import Terminado

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
async def notebook():
    # Start the notebook
    notebook = NotebookTestBase()
    notebook.setup_class()
    notebook.wait_until_alive()
    yield notebook
    notebook.teardown_class()


async def test_terminado_client_auth(notebook):
    # NotebookTestBase uses "/a%40b/" as a hub prefix, we have to make sure we don't escape that
    notebook_url = URL(notebook.base_url(), encoded=True)

    # Connect to the terminal with a dummy token
    with pytest.raises(KeyError, match="name"):
        async with ClientSession() as client, Terminado(notebook_url, "fake", client) as terminado_client:
            assert terminado_client.terminal_name == "1"

    # Connect to the terminal with the real token
    async with ClientSession() as client, Terminado(notebook_url, notebook.token, client) as terminado_client:
        assert terminado_client.terminal_name == "1"


async def test_terminado_stdin(notebook):
    notebook_url = URL(notebook.base_url(), encoded=True)

    # Connect to the terminal with the real token
    async with ClientSession() as client, Terminado(notebook_url, notebook.token, client) as terminado_client:
        cmd = f'touch {notebook.home_dir}/hello.txt\n'
        await terminado_client.send_stdin(cmd)
        print(os.listdir(notebook.home_dir))
