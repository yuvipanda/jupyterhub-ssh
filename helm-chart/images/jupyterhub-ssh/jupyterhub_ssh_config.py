from ruamel.yaml import YAML

yaml = YAML()
with open("/etc/jupyterhub-ssh/config/values.yaml") as f:
    config = yaml.load(f)

c.JupyterHubSSH.host_key_path = "/etc/jupyterhub-ssh/config/hostKey"
c.JupyterHubSSH.hub_url = config["hubUrl"]
c.JupyterHubSSH.debug = True
