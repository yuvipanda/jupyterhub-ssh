FROM python:3.8-slim

WORKDIR /srv/jupyterhub-ssh

ENV NB_UID=1000
ENV NB_USER jovyan

RUN adduser \
    --disabled-password \
    --shell "/sbin/nologin" \
    --gecos "Default Jupyter user" \
    --uid ${NB_UID} \
    ${NB_USER}

COPY . .
COPY helm-chart/images/jupyterhub-ssh/jupyterhub_ssh_config.py .

RUN pip3 install --no-cache-dir .

USER $NB_UID

ENTRYPOINT [ "python3", "-m", "jupyterhub_ssh" ]
