import re

from setuptools import setup


version = ""
with open("jinja2_static/__init__.py") as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

requirements = []
with open("requirements.txt") as f:
    requirements = f.read().splitlines()


setup(
    name="jinja2_static",
    author="AlexFlipnote",
    url="https://github.com/AlexFlipnote/jinja2_static",
    description="Converts Flask/Jinja2 template files to static files.",
    version=version,
    packages=["jinja2_static"],
    include_package_data=True,
    install_requires=requirements
)
