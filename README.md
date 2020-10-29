# JupyterHub SSH and SFTP

[![Documentation build status](https://img.shields.io/readthedocs/jupyterhub?logo=read-the-docs)](https://jupyterhub-ssh.readthedocs.io/en/latest/)

Access through [SSH](https://www.ssh.com/ssh) any JupyterHub, regardless how it was deployed and easily transfer files through [SFTP](https://www.ssh.com/ssh/sftp).

## Development Status
This project is under active develpoment :tada:, so expect a few changes along the way.

## Technical Overview

The JupyterHubSSH service is used for SSH access to your hub. `JupyterHubSSH` is made up of two main components:

- an SSH server that maps a SSH connection to a Notebook server on a JupyterHub.
- a [Terminado](https://github.com/jupyter/terminado) client that knows how to connect and communicate to a Jupyter terminal.

![Overview](https://raw.githubusercontent.com/yuvipanda/jupyterhub-ssh/main/docs/source/_static/images/technical-overview.png)

Apart from SSH access to JupyterHub, once `jupyterhub-ssh` was deployed, you can also use it to tranfer files from your local
home directory into your remote hub home directory. This is achieved through `jupyterhub-sftp`, a service that provides a SFTP
setup using [OpenSSH](https://www.openssh.com/). `jupyterhub-sftp` currently supports only [NFS](https://tldp.org/LDP/nag/node140.html)
based home directories.

## Installation

Instructions on how to install and deploy JupyterHub SSH & SFTP services.

### Regular deployment

1. Clone the repo and install the jupyterhub-ssh package:
	``` bash
	$ git clone https://github.com/yuvipanda/jupyterhub-ssh.git
	$ cd jupyterhub-ssh
	$ pip install -e .
	```
1. Or install the package directly:
	``` bash
	$ pip install git+https://github.com/yuvipanda/jupyterhub-ssh.git
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

### Kuberbetes based deployment
If your JupyterHub was deployed using Kubernetes, you can use the Helm charts available in this repo to deploy JupyterHub SSH & SFTP
directly into your Kubernetes cluster.

	```bash
	# Let helm the command line tool know about a Helm chart repository
	# that we decide to name jupyterhub.
	$ helm repo add jupyterhub-ssh https://yuvipanda.github.io/jupyterhub-ssh/
	$ helm repo update

	# Simplified example on how to install a Helm chart from a Helm chart repository
	# named jupyterhub-ssh. See the Helm chart's documentation for additional details
	# required.
	$ helm install jupyterhub-ssh/jupyterhub-ssh --version <helm chart version> --set hubUrl=https://jupyter.example.org --set-file hostKey=<path to a private SSH key>
	```

## How to use it

### How to SSH
1. Login into your JupyterHub and go to `https://<hub-address>/hub/token`.
2. Copy the token from JupyterHub.
3. SSH into JupyterHub:
	```bash
	$ ssh <username-you-used>@<hub-address>
	```
4. Enter the token received from JupyterHub as a password.
5. TADA :tada: Now you have an interactive terminal! You can do anything you would generally interactively do via ssh: run editors,
fully interactive programs, use the commandline, etc. Some features like non-interactive command running, tunneling, etc are currently
unavailable.

### How to SFTP
1. Login into your JupyterHub and go to `https://<hub-address>/hub/token`.
2. Copy the token from JupyterHub.
3. Transfer file into Jupyterhub:
	* Using the `sftp` command:
		```bash
		$ sftp <hub-username>@<hub-address>
		```
4. Enter the token received from JupyterHub as a password.
5. TADA :tada: Now you can transfer files to and from your home directory on the hubs.
