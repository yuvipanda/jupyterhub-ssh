# JupyterHub SSH

[![Documentation build status](https://img.shields.io/readthedocs/jupyterhub?logo=read-the-docs)](https://jupyterhub-ssh.readthedocs.io/en/latest/)

SSH Access to JupyterHubs, independent of the way there were deployed.

## Development Status
This project is under active develpoment :tada:, so expect a few changes along the way.

## Technical Overview

JupyterHubSSH is made up of two main components:

- a Notebook SSH server that maps a SSH connection to a Notebook server on a JupyterHub.
- a [Terminado](https://github.com/jupyter/terminado) client that knows how to connect and communicate to a Jupyter terminal.

![Overview](https://raw.githubusercontent.com/yuvipanda/jupyterhub-ssh/main/docs/source/_static/images/technical-overview.png)

## Installation

1. Clone the repo and install the jupyterhub-ssh package:
``` bash
$ git clone https://github.com/yuvipanda/jupyterhub-ssh.git
$ cd jupyterhub-ssh
$ pip install .
```
1. Or install the package directly:
``` bash
pip install git+https://github.com/yuvipanda/jupyterhub-ssh.git
```

2. Create the config file:
```bash
$ touch jupyterhub_ssh_config.py
```

3. Put in the config file at least the following two config options:
* `c.JupyterHubSSH.hub_url`: URL of JupyterHub to connect to.
* `c.JupyterHubSSH.host_key_path`: Path to host's private SSH Key.

	More configuration options can be found in the docs [here](https://jupyterhub-ssh.readthedocs.io/en/latest/api/index.html#module-jupyterhub_ssh).

5. Start the JupyterHubSSH app from the directory where the config file
`jupyterhub_ssh_config.py` is located:
```bash
$ python -m jupyterhub_ssh
```

## Instructions on how to use it

1. Login into your JupyterHub and go to `https://<hub-address>/hub/token`.
2. Copy the token from JupyterHub.
3. SSH into JupyterHub:
```bash
$ ssh <username-you-used>@<hub-address>
```
4. Enter the token received from JupyterHub as a password.
5. TADA :tada:
