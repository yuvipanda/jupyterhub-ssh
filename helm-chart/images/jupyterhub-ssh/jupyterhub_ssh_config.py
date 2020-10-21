from ruamel.yaml import YAML

yaml = YAML()

c.JupyterHubSSH.host_key_path = '/etc/jupyterhub-ssh/secrets/jupyterhub-ssh.host-key'
c.JupyterHubSSH.debug = True

with open('/etc/jupyterhub-ssh/config/values.yaml') as f:
    config = yaml.load(f)


c.JupyterHubSSH.hub_url = config['hubUrl']
