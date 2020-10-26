#!/usr/bin/env python3
"""
Verify that a JupyterHub token is valid for a given user

# SECURITY WARNING!!!!

This code runs as **ROOT**, and deals with **User Input**
(in the form of username), manipulating paths on the host filesystem.
This requires a very high standard for securing it, since security
lapses here will lead to exposing users' home directories. At
the very least, watch out for the following classes of vulnerabilities:

1. Path Traversal Attacks - https://owasp.org/www-community/attacks/Path_Traversal
2. Arbitrary code execution vulnerabilities in YAML
3. Loading python libraries *not* owned by root. This script should *not*
   be in a venv owned by anything other than root. Preferably, this should
   just use debian packages.
4. Sending hub tokens to arbitrary URLs, not just the configured hub

There's gonna be more, but really - just watch out!

# bind mounting and chroot

sshd supports chrooting to a given directory after authenticating as
a user. This is required for SFTP so we can expose *just* a user's
home directory to them, without accidentally also exposing other
users' home directories. sshd requires that all the directories in the
path - including the user's home directory - are owned by root and
not writeably by anyone else. This is a little problematic for our
use case - JupyterHub home directories are usually writeable by
the user. So we can't directly chroot to the directories. We also
can't just chroot to the parent directory - it contains all the
users' home directories, and they're all usually owned by the same uid
(1000).

So in *this* script, we do some bind mounting magic to make this work.
We provision a directory (${DEST_DIR}) owned by root. For each user
who successfully logs in, we:

1. Create an empty, root owned directory (${DEST_DIR}/${USERNAME})
2. Create another empty, root owned directory inside this -
   (${DEST_DIR}/${USERNAME}/${USERNAME}). This will act as a
   bind target only.
3. Bind mount the user's actual home directory (${SRC_DIR}/${USERNAME})
   to this nested directory (${DEST_DIR}/${USERNAME}/${USERNAME}).
4. Make sshd chroot to the first level directory (${DEST_DIR}/${USERNAME}).
   This is root owned, so it's fine.
5. Tell sftp to start in the subdirectory where our user's home directory
   has been bind mounted (${DEST_DIR}/${USERNAME}/${USERNAME}). This shows
   them their home directory when they log in, but at most they can
   escape to the parent directory - nowhere else, thanks to the proper
   chrooting.

We do this if needed the first time a user logs in. However, the user
controls ${USERNAME}. If we aren't careful, they can use it to have us
give them read (and possibly write) access to *any* part of the filesystem.
So we have to be very careful doing this.
"""
import sys
import os
import subprocess
import requests
from ruamel.yaml import YAML

yaml = YAML(typ='safe')

def valid_user(hub_url, username, token):
    """
    Check if token is valid for username in hub at hub_url
    """
    # FIXME: Construct this URL better? 
    url = f'{hub_url}/hub/api/user'
    headers = {
        'Authorization': f'token {token}'
    }
    resp = requests.get(url, headers=headers)
    return resp.status_code == 200

# Directory containing user home directories
SRC_DIR = '/mnt/home'
# Directory sshd is exposing. We will bind-mount users there
DEST_DIR = '/export/home'

def bind_mount_user(untrusted_username):
    # username is user controlled data, so should be treated more cautiously
    # It's been authenticated as valid by sshd, but that doesn't mean anything
    # FIXME: Am pretty sure this is BAD
    # FIXME: escape username?
    src_path = os.path.abspath(os.path.join(SRC_DIR, untrusted_username))
    dest_chroot_path = os.path.abspath(os.path.join(DEST_DIR, untrusted_username))
    dest_bind_path = os.path.join(dest_chroot_path, untrusted_username)

    if not os.path.exists(dest_chroot_path):
        os.makedirs(dest_chroot_path, exist_ok=True)
        os.makedirs(dest_bind_path, exist_ok=True)
        subprocess.check_call([
            'mount', '-o', 'bind',
            src_path, dest_bind_path
        ])

# PAM_USER is passed in to us by pam_exec: http://www.linux-pam.org/Linux-PAM-html/sag-pam_exec.html
# We *must* treat this as untrusted. From `pam_exec`'s documentation:
# >  Commands called by pam_exec need to be aware of that the user can have control over the environment.
untrusted_username = os.environ['PAM_USER']
# FIXME: Find a way to validate this to be a trusted username?

# Password is a null delimited string, passed in via stdin by pam_exec
password = sys.stdin.read().rstrip('\x00')

# We read the config file *just* to get the hub URL
# FIXME: Maybe get rid of the YAML dependency here?
# FIXME: Make sure the file is owned by root & has proper perms!
with open('/etc/jupyterhub-ssh/config/values.yaml') as f:
    config = yaml.load(f)

hub_url = config['hubUrl']

if valid_user(hub_url, untrusted_username, password):
    # FIXME: We're doing a bind mount here based on an untrusted_username
    # THIS IS *SCARY* and we should do more work to ensure we aren't
    # accidentally exposing user data.
    bind_mount_user(untrusted_username)
    sys.exit(0)

sys.exit(1)
