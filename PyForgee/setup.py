#!/usr/bin/env python3
"""
PyForgee - Outil Python-to-EXE avancé
Un outil hybride pour compiler des scripts Python en exécutables optimisés
"""

from setuptools import setup, find_packages
import os
import sys

# Version du package
__version__ = "1.0.0"

# Lecture du README
def read_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

# Lecture des requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="PyForgee",
    version=__version__,
    author="PyForgee Team",
    author_email="contact@PyForgee.dev",
    description="Outil Python-to-EXE avancé avec optimisations et protection",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/PyForgee/PyForgee",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Compilers",
    ],
    python_requires=">=3.9",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "PyForgee=cli.main_cli:main",
            "PyForgee-gui=gui.main_window:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.json", "*.txt"],
    },
    zip_safe=False,
)