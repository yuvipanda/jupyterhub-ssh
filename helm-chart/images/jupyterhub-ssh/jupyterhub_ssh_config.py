from ruamel.yaml import YAML

yaml = YAML()
with open("/etc/jupyterhub-ssh/config/values.yaml") as f:
    config = yaml.load(f)

# FIXME: help this config migrate to ssh.config as well
c.JupyterHubSSH.hub_url = config["hubUrl"]

# load generic configuration
for app, cfg in config["ssh"]["config"].items():
    c[app].update(cfg)
