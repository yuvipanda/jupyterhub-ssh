#!/usr/bin/env python3
"""
Generate architecture diagrams for the documentation
"""
from diagrams import Diagram, Edge, Cluster
from diagrams.k8s.compute import Deployment, Pod
from diagrams.k8s.network import Service
from diagrams.k8s.storage import PVC

IMAGES_DIR = "source/_static/images"

with Diagram("JupyterHub + SSH + SFTP", show=False, outformat="png", filename=f"{IMAGES_DIR}/architecture") as diag:
    autohttps = Deployment("autohttps")
    ssh = autohttps >> Edge(label="port 22") >> Deployment("jupyterhub-ssh")
    sftp = autohttps >> Edge(label="port 2222") >> Deployment("jupyterhub-sftp")

    homedirs = PVC("home directories")

    sftp - homedirs

    with Cluster("jupyterhub"):
        hub = Deployment("hub/proxy")

        hub_svc = autohttps >> Edge(label="port 80") >> hub

        ssh >> Edge(label="start server if needed", style="bold") >> hub

        users = [Pod(f"user{i}") for i in range(2)]

        for user in users:
            user - homedirs

        for user in users:
            ssh - Edge(label="console via terminado", color="red", style="bold") - user
        hub >> users
