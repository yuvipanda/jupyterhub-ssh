FROM buildpack-deps:focal

RUN apt-get update -y > /dev/null \
 && apt-get upgrade -y > /dev/null \
 && apt-get install -y \
        openssh-server \
        python3 \
        python3-pip \
 && rm -rf /var/lib/apt/lists/*

# Setup the jovyan user everyone will impersonate
ENV NB_UID=1000 \
    NB_USER=jovyan
RUN adduser \
    --disabled-password \
    --shell "/sbin/nologin" \
    --gecos "Default Jupyter user" \
    --uid ${NB_UID} \
    ${NB_USER}

# Setup Name Service Switch (NSS) All-To-One (ATO) logic
# - It map unknown users to the jovyan user
# - Setup involves git clone and C code compilation
#
# FIXME: Slim down image to not include gcc etc. as is required to compile this
#        software by using a dedicated build step from which we later copy the
#        compiled software from.
#
COPY setup-nss.bash /tmp/
RUN /tmp/setup-nss.bash && rm /tmp/setup-nss.bash
COPY libnss-ato.conf nsswitch.conf /etc/

# Setup our custom Python logic
# - It couples PAM auth to the verification of JupyterHub tokens
#
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt
COPY jupyterhub-token-verify.py /usr/sbin/
COPY pam-common-auth /etc/pam.d/

# Setup SSHD - The OpenSSH server process
# - /export/home is what sshd will expose
# - /run/sshd is referred to as a privilege separation dir (what is it?)
#
# sshd reference:
# -D    sshd will not detach and does not become a daemon
# -e    sshd will send the output to the standard error instead of the system
#       log.
#
# NOTE: sshd listens to SIGTERM and not just SIGKILL, so terminating this
#       container will be quick as it should be.
#
RUN mkdir -p \
        /export/home \
        /run/sshd
COPY sshd_config /etc/ssh/
EXPOSE 2222
CMD ["/usr/sbin/sshd", "-De"]
