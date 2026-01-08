#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup script for BESS Simulation Package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bess_sim",
    version="2.0.0",
    author="RTU Institute of Power Engineering",
    author_email="karlis.baltputnis@rtu.lv",
    description="BESS Reserve Provision Simulation Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "matplotlib>=3.4.0",
        "openpyxl>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "bess_sim=bess_sim.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.xlsx", "*.csv"],
    },
)
