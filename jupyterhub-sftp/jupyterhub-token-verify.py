#!/usr/bin/env python3
import sys
import os
import subprocess
import requests
from ruamel.yaml import YAML

yaml = YAML(typ='safe')

def valid_user(hub_url, username, token):
    url = f'{hub_url}/hub/api/user'
    headers = {
        'Authorization': f'token {token}'
    }
    resp = requests.get(url, headers=headers)
    return resp.status_code == 200

SRC_DIR = '/mnt/home'
DEST_DIR = '/export/home'

def bind_mount_user(username):
    # username is user controlled data, so should be treated more cautiously
    # It's been authenticated as valid by sshd, but that doesn't mean anything
    # FIXME: Am pretty sure this is BAD
    # FIXME: escape username?
    src_path = os.path.abspath(os.path.join(SRC_DIR, username))
    dest_chroot_path = os.path.abspath(os.path.join(DEST_DIR, username))
    dest_bind_path = os.path.join(dest_chroot_path, username)

    if not os.path.exists(dest_chroot_path):
        os.makedirs(dest_chroot_path, exist_ok=True)
        os.makedirs(dest_bind_path, exist_ok=True)
        subprocess.check_call([
            'mount', '-o', 'bind',
            src_path, dest_bind_path
        ])

username = os.environ['PAM_USER']
password = sys.stdin.read().rstrip('\x00')

with open('/etc/jupyterhub-ssh/config/values.yaml') as f:
    config = yaml.load(f)

if valid_user(config['hubUrl'], username, password):
    bind_mount_user(username)
    sys.exit(0)

sys.exit(1)
