FROM python:3.8-slim

# Ensure Python logs are made available for k8s directly
ENV PYTHONUNBUFFERED=1

# Prepare a user
ENV NB_UID=1000 \
    NB_USER=jovyan
RUN adduser \
    --disabled-password \
    --shell "/sbin/nologin" \
    --gecos "Default Jupyter user" \
    --uid ${NB_UID} \
    ${NB_USER}

# FIXME: This isn't great, consider for example locally building and pushing an
#        image, then one could very well end up embedding sensitive content into
#        something one has made public.
WORKDIR /srv/jupyterhub-ssh
COPY . .
COPY helm-chart/images/jupyterhub-ssh/jupyterhub_ssh_config.py .

# Install jupyterhub_ssh the Python package
RUN pip3 install --no-cache-dir .

# Configure to run jupyterhub_ssh
USER $NB_UID
ENTRYPOINT [ "python3", "-m", "jupyterhub_ssh" ]
