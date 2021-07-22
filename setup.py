import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="jupyterhub-ssh",
    version="0.1",
    author="Yuvi Panda",
    author_email="yuvipanda@gmail.com",
    description="SSH access to JupyterHubs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yuvipanda/jupyterhub-ssh",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "jupyterhub",
        "asyncssh",
        "aiohttp",
        "yarl",
        "websockets",
        "async-timeout",
    ],
)
