"""
Module used by the Harness Instruqt Workshops
  Created by: Joe Titra
  Version: 0.1.2
  Description: Common Functions used across the Instruqt SE Workshops
  History:
    Version    |    Author    |    Date    |  Comments
    v0.1.0     | Joe Titra    | 06/21/2024 | Intial version migrating from bash
    v0.1.1     | Joe Titra    | 06/24/2024 | Added functions for HCE
    v0.1.2     | Joe Titra    | 06/25/2024 | updated apply_k8s_manifests and create_systemd_service

apply_k8s_manifests
"""
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyharnessinstruqt",
    version="0.1.2",
    description="Common Functions used across the Instruqt SE Workshops",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Joe Titra",
    author_email="jtitra@harness.io",
    license="MIT License",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    install_requires=[
        "requests",
        "jinja2",
        "kubernetes",
        "pyyaml"
    ]
)
