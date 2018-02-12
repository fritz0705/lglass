#!/usr/bin/env python3

"""lglass is a collection of code and data files written in Python. It is designed
to support registries in their work and to provide public services for access
to the database."""

import setuptools

setuptools.setup(
    name="lglass",
    version="1.1",
    packages=[
        "lglass",
        "lglass.whois",
    ],
    author="Fritz Grimpen",
    author_email="fritz@grimpen.net",
    url="https://github.com/fritz0705/lglass.git",
    license="http://opensource.org/licenses/MIT",
    description="Provides tools for IRR databases",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration"
    ],
    long_description=__doc__,
    install_requires=[
        "netaddr",
        "python-dateutil"
    ],
    entry_points={
        "console_scripts": [
            "lipam = lglass.lipam:main"
        ]
    },
    package_data={
    }
)
