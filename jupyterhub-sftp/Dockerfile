FROM buildpack-deps:focal

RUN apt update --yes > /dev/null && \
    apt install --yes openssh-server python3 python3-venv > /dev/null

ENV NB_UID=1000
ENV NB_USER jovyan
ENV VENV_PATH /opt/venv

RUN adduser \
    --disabled-password \
    --shell "/sbin/nologin" \
    --gecos "Default Jupyter user" \
    --uid ${NB_UID} \
    ${NB_USER}

# Setup NSS so all users are mapped to jovyan
COPY setup-nss.bash /tmp/setup-nss.bash
RUN /tmp/setup-nss.bash && rm /tmp/setup-nss.bash
COPY libnss-ato.conf /etc/libnss-ato.conf
COPY nsswitch.conf /etc/nsswitch.conf

COPY pam-common-auth /etc/pam.d/common-auth

RUN python3 -m venv ${VENV_PATH}
# FIXME: Get this from a fully frozen requirements.txt file plz
RUN ${VENV_PATH}/bin/pip install --no-cache escapism requests ruamel.yaml

COPY jupyterhub-token-verify.py /usr/sbin/jupyterhub-token-verify.py

# Setup SSHD
# Privilege separation dir (not sure what that is!) needed by sshd
RUN mkdir /run/sshd
COPY sshd_config /etc/ssh/sshd_config

RUN mkdir -p /export/home

EXPOSE 2222
CMD ["/usr/sbin/sshd", "-De"]
