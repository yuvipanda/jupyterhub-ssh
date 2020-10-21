FROM python:3.8-slim

WORKDIR /srv/jupyterhub-ssh

COPY . .
COPY helm-chart/images/jupyterhub-ssh/jupyterhub_ssh_config.py .

RUN pip3 install --no-cache-dir .

ENTRYPOINT [ "python3", "-m", "jupyterhub_ssh" ]
