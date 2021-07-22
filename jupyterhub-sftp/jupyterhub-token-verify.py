#!/opt/venv/bin/python3
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
3. Sending hub tokens to arbitrary URLs, not just the configured hub

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
import os
import string
import subprocess
import sys
from pathlib import PosixPath

import requests
from escapism import escape


def valid_user(hub_url, username, token):
    """
    Check if token is valid for username in hub at hub_url
    """
    # FIXME: Construct this URL better?
    url = f"{hub_url}/hub/api/user"
    headers = {"Authorization": f"token {token}"}
    resp = requests.get(url, headers=headers)
    return resp.status_code == 200


# Directory containing user home directories
SRC_DIR = PosixPath("/mnt/home")
# Directory sshd is exposing. We will bind-mount users there
DEST_DIR = PosixPath("/export/home")


def bind_mount_user(untrusted_username):
    # username is user controlled data, so should be treated more cautiously
    # It's been authenticated as valid by sshd, but that doesn't mean anything
    # However, the untrusted username is what sshd will use as chroot, so we
    # have to do our bind mounts there.
    #

    # In JupyterHub, we escape most file system naming interactions with this
    # escapism call. This should also work here to make sure we mount the correct
    # directory.
    # FIXME: Verify usernames starting with '-' work fine with PAM & NSS
    safe_chars = set(string.ascii_lowercase + string.digits)
    source_username = escape(
        untrusted_username, safe=safe_chars, escape_char="-"
    ).lower()

    # To protect against path traversal attacks, we:
    # 1. Resolve our paths to absolute paths, traversing any symlinks if needed
    # 2. Make sure that the absolote paths are within the source directories appropriately
    # This prevents any relative path (..) or symlink attacks.
    src_path = (SRC_DIR / source_username).resolve()

    # Make sure src_path isn't outside of SRC_DIR
    # And doesn't refer to other users' home directories
    assert str(src_path.relative_to(SRC_DIR)) == source_username

    dest_chroot_path = (DEST_DIR / untrusted_username).resolve()
    # Make sure dest_chroot_path isn't outside of DEST_DIR
    assert str(dest_chroot_path.relative_to(DEST_DIR)) == untrusted_username

    dest_bind_path = (dest_chroot_path / untrusted_username).resolve()
    # Make sure dest_bind_path isn't outside dest_chroot_path
    assert str(dest_bind_path.relative_to(dest_chroot_path)) == untrusted_username

    if not os.path.exists(dest_chroot_path):
        os.makedirs(dest_chroot_path, exist_ok=True)
        os.makedirs(dest_bind_path, exist_ok=True)
        subprocess.check_call(["mount", "-o", "bind", src_path, dest_bind_path])


# PAM_USER is passed in to us by pam_exec: http://www.linux-pam.org/Linux-PAM-html/sag-pam_exec.html
# We *must* treat this as untrusted. From `pam_exec`'s documentation:
# >  Commands called by pam_exec need to be aware of that the user can have control over the environment.
untrusted_username = os.environ["PAM_USER"]

# Password is a null delimited string, passed in via stdin by pam_exec
password = sys.stdin.read().rstrip("\x00")

with open("/etc/jupyterhub-sftp/config/hubUrl", "r") as f:
    hub_url = f.read()

if valid_user(hub_url, untrusted_username, password):
    # FIXME: We're doing a bind mount here based on an untrusted_username
    # THIS IS *SCARY* and we should do more work to ensure we aren't
    # accidentally exposing user data.
    bind_mount_user(untrusted_username)
    sys.exit(0)

sys.exit(1)
