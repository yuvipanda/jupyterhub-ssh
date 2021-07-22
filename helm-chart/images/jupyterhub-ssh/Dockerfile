# To build this Dockerfile locally:
#
#   docker build --tag jupyterhub-ssh ../../.. -f Dockerfile
#
FROM python:3.8-slim

RUN apt-get update -y > /dev/null \
 && apt-get upgrade -y > /dev/null \
 && apt-get install -y \
        wget \
 && rm -rf /var/lib/apt/lists/*

# Setup tini
# - tini helps ensure SIGTERM propegate to python3 when "docker stop
#   <container>" or "kubectl delete <pod>" sends the SIGTERM signal, which makes
#   the container terminate quickly in a controlled manner.
# - tini reference: https://github.com/krallin/tini
#
RUN ARCH=`uname -m`; \
    if [ "$ARCH" = x86_64 ]; then ARCH=amd64; fi; \
    if [ "$ARCH" = aarch64 ]; then ARCH=arm64; fi; \
    wget -qO /tini "https://github.com/krallin/tini/releases/download/v0.19.0/tini-$ARCH" \
 && chmod +x /tini
ENTRYPOINT ["/tini", "--"]

# Prepare a user to run as
ENV NB_UID=1000 \
    NB_USER=jovyan
RUN adduser \
    --disabled-password \
    --shell "/sbin/nologin" \
    --gecos "Default Jupyter user" \
    --uid ${NB_UID} \
    ${NB_USER}
USER $NB_UID

# Install jupyterhub_ssh the Python package
WORKDIR /srv/jupyterhub-ssh
COPY jupyterhub_ssh ./jupyterhub_ssh
COPY setup.py LICENSE README.md ./
COPY helm-chart/images/jupyterhub-ssh/jupyterhub_ssh_config.py ./
RUN pip3 install --no-cache-dir .

# Configure to run jupyterhub_ssh
# - PYTHONUNBUFFERED help make Python logs made available for k8s directly
#
ENV PYTHONUNBUFFERED=1
CMD ["python3", "-m", "jupyterhub_ssh"]
