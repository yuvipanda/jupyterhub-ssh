# JupyterHub SSH and SFTP

[![Documentation build status](https://img.shields.io/readthedocs/jupyterhub-ssh?logo=read-the-docs)](https://jupyterhub-ssh.readthedocs.io/en/latest/)
[![GitHub Workflow Status - Test](https://img.shields.io/github/workflow/status/jupyterhub/zero-to-jupyterhub-k8s/Test%20chart?logo=github&label=tests)](https://github.com/jupyterhub/zero-to-jupyterhub-k8s/actions)

Access through [SSH](https://www.ssh.com/ssh) any JupyterHub, regardless how it was deployed and easily transfer files through [SFTP](https://www.ssh.com/ssh/sftp).
With a JupyterHub [SSH](https://www.ssh.com/ssh) server deployed, you can start and access your JupyterHub user environment through SSH. With a JupyterHub
[SFTP](https://www.ssh.com/ssh/sftp) server deployed alongside the JupyterHub's user storage, you can use SFTP to work against your JupyterHub user's home directory.
These services are authenticated using an access token acquired from your JupyterHub's user interface under `/hub/token`.

## Development Status

This project is under active develpoment :tada:, so expect a few changes along the way.

## Technical Overview

The JupyterHub SSH service provides SSH access to your user environment in a JupyterHub. JupyterHub SSH is made up of two main components:

- an SSH server that maps a SSH connection to a Notebook server on a JupyterHub.
- a [Terminado](https://github.com/jupyter/terminado) client that knows how to connect and communicate to a Jupyter terminal.

![Overview](https://raw.githubusercontent.com/yuvipanda/jupyterhub-ssh/main/docs/source/_static/images/technical-overview.png)

Apart from SSH access to JupyterHub, once `jupyterhub-ssh` was deployed, you can also use it to transfer files from your local
home directory into your remote hub home directory. This is achieved through `jupyterhub-sftp`, a service that provides a SFTP
setup using [OpenSSH](https://www.openssh.com/). `jupyterhub-sftp` currently supports only [NFS](https://tldp.org/LDP/nag/node140.html)
based home directories.

## Installation

Instructions on how to install and deploy JupyterHub SSH & SFTP services.

### Regular deployment (jupyterhub ssh only)

1. Clone the repo and install the jupyterhub-ssh package:

   ```bash
   $ git clone https://github.com/yuvipanda/jupyterhub-ssh.git
   $ cd jupyterhub-ssh
   $ pip install -e .
   ```

1. Or install the package directly:

   ```bash
   $ pip install git+https://github.com/yuvipanda/jupyterhub-ssh.git
   ```

1. Create the config file:

   ```bash
   $ touch jupyterhub_ssh_config.py
   ```

1. Put in the config file at least the following two config options:

   - `c.JupyterHubSSH.hub_url`: URL of JupyterHub to connect to.
   - `c.JupyterHubSSH.host_key_path`: Path to host's private SSH Key.

   More configuration options can be found in the docs [here](https://jupyterhub-ssh.readthedocs.io/en/latest/api/index.html#module-jupyterhub_ssh).

1. Start the JupyterHubSSH app from the directory where the config file
   `jupyterhub_ssh_config.py` is located:

   ```bash
   python -m jupyterhub_ssh
   ```

### Kubernetes based deployment (jupyterhub ssh and/or sftp)

If your JupyterHub has been deployed to Kubernetes, you can use the Helm chart
available in this repo to deploy JupyterHub SSH and/or JupyterHub SFTP directly
into your Kubernetes cluster.

```bash
helm install <helm-release-name> \
   --repo https://yuvipanda.github.io/jupyterhub-ssh/ jupyterhub-ssh \
   --version <helm chart version> \
   --set hubUrl=https://jupyter.example.org \
   --set ssh.enabled=true \
   --set sftp.enabled=false
```

If you install JupyterHub SFTP, then it needs access to the home folders. These
home folders are assumed to be exposed via a k8s PVC resource that you should
name via the `sftp.pvc.name` configuration.

If your JupyterHub has been deployed using [the official JupyterHub Helm
chart](https://z2jh.jupyter.org) version 1.1.0 or later, and you have
_configured the official JupyterHub Helm chart_ with `proxy.https.enabled=true`
and `proxy.https.type=letsencrypt`, then you can add the following to to acquire
access to the jupyterhub-ssh and jupyterhub-sftp services via that setup.

```yaml
# Configuration for the official JupyterHub Helm chart to accept traffic via
proxy:
   https:
      enabled: true
      type: letsencrypt
      letsencryptEmail: <my-email-here>

   service:
     # jupyterhub-ssh/sftp integration part 1/3:
     #
     # We must accept traffic to the k8s Service (proxy-public) receiving traffic
     # from the internet. Port 22 is typically used for both SSH and SFTP, but we
     # can't use the same port for both so we use 23.
     #
     extraPorts:
       - name: ssh
         port: 22
         targetPort: ssh
       - name: sftp
         port: 23
         targetPort: sftp

   traefik:
     # jupyterhub-ssh/sftp integration part 2/3:
     #
     # We must accept traffic arriving to the autohttps pod (traefik) from the
     # proxy-public service. Expose a port and update the NetworkPolicy
     # to tolerate incoming (ingress) traffic on the exposed port.
     #
     extraPorts:
       - name: ssh
         containerPort: 8022
       - name: sftp
         containerPort: 8023
     networkPolicy:
       allowedIngressPorts: [http, https, ssh]

     # jupyterhub-ssh/sftp integration part 3/3:
     #
     # We must let traefik know it should listen for traffic (traefik entrypoint)
     # and route it (traefik router) onwards to the jupyterhub-ssh k8s Service
     # (traefik service).
     #
     extraStaticConfig:
       entryPoints:
         ssh-entrypoint:
           address: :8022
         ssh-entrypoint:
           address: :8023
     extraDynamicConfig:
       tcp:
         services:
           ssh-service:
             loadBalancer:
               servers:
                 - address: jupyterhub-ssh:22
           sftp-service:
             loadBalancer:
               servers:
                 - address: jupyterhub-sftp:22
         routers:
           ssh-router:
             entrypoints:
               - ssh-entrypoint
             rule: HostSNI(`*`)
             service: ssh-service
           sftp-router:
             entrypoints:
               - sftp-entrypoint
             rule: HostSNI(`*`)
             service: sftp-service
```

## How to use it

### How to SSH

1. Login into your JupyterHub and go to `https://<hub-address>/hub/token`.

2. Copy the token from JupyterHub.

3. SSH into JupyterHub:

   ```bash
   ssh <hub-username>@<hub-address>
   ```

4. Enter the token received from JupyterHub as a password.

5. TADA :tada: Now you have an interactive terminal! You can do anything you would generally interactively do via ssh: run editors,
   fully interactive programs, use the commandline, etc. Some features like non-interactive command running, tunneling, etc are currently
   unavailable.

### How to SFTP

1. Login into your JupyterHub and go to `https://<hub-address>/hub/token`.

2. Copy the token from JupyterHub.

3. Transfer file into Jupyterhub:

   - Using the `sftp` command:

     ```bash
     sftp <hub-username>@<hub-address>
     ```

4. Enter the token received from JupyterHub as a password.

5. TADA :tada: Now you can transfer files to and from your home directory on the hubs.
