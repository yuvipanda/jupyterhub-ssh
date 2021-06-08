from ruamel.yaml import YAML
from pathlib import Path

sshConnTimeout = Path("/etc/jupyterhub-ssh/config/sshConnTimeout").read_text()

yaml = YAML()
with open("/etc/jupyterhub-ssh/config/values.yaml") as f:
    config = yaml.load(f)

c.JupyterHubSSH.host_key_path = "/etc/jupyterhub-ssh/config/hostKey"
c.JupyterHubSSH.hub_url = config["hubUrl"]
c.JupyterHubSSH.debug = True
c.JupyterHubSSH.ssh_conn_timeout = int(sshConnTimeout)
