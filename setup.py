#!/usr/bin/env python3

import distutils.core

with open("README.md") as f:
	long_description = f.read()

distutils.core.setup(
	name="lglass",
	version="1.0dev",
	packages=["lglass"],
	author="Fritz Grimpen",
	author_email="fritz@grimpen.net",
	url="https://github.com/fritz0705/lglass.git",
	license="http://opensource.org/licenses/MIT",
	description="lglass is a library which provides simple tools for working with RPSL databases",
	classifiers=[
		"Development Status :: 4 - Beta",
		"Operating System :: POSIX",
		"Programming Language :: Python :: 3.3",
		"Topic :: Internet :: Log Analysis",
		"Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
		"Topic :: System :: Networking",
		"Topic :: System :: Systems Administration"
	],
	long_description=long_description,
	install_requires=[
		"netaddr>=0.7.10",
		"bottle>=0.11.6",
		"Jinja2>=2.7",
		"MarkupSafe>=0.18"
	]
)

