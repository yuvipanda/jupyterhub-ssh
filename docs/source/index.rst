.. JupyterHub-SSH documentation master file, created by
   sphinx-quickstart on Fri Oct 23 15:23:33 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=======================
JupyterHub SSH and SFTP
=======================

 - An SSH interface to JupyterHub
 - A tranfer file utility using SFTP

Regardless of the way JupyterHub was deployed, JupyterHub SSH can be deployed too on that infrastructure and used as an
SSH interface to your Hub. SSH access provides the exact same environment (packages, home directory, etc) as web-based
access to JupyterHub. You can do anything you would generally interactively do via `ssh` like use the commandline, or
run editors or fully interactive programs, etc. Some features, like non-interactive command running, tunneling, etc are
not yet available, though. File transfer to and from your home directory on the hub is also possible through SFTP.

Contents
========

API Reference
-------------

.. toctree::
   :maxdepth: 3

   api/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
