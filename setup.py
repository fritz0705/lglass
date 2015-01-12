#!/usr/bin/env python3

"""lglass is a collection of code and data files written in Python. It is designed
to support registries in their work and to provide public services for access
to the database."""

import setuptools

setuptools.setup(
	name="lglass",
	version="1.0",
	packages=[
		"lglass",
		"lglass.database",
		"lglass.generators",
		"lglass.tools",
		"lglass.web",
	],
	author="Fritz Grimpen",
	author_email="fritz@grimpen.net",
	url="https://github.com/fritz0705/lglass.git",
	license="http://opensource.org/licenses/MIT",
	description="provides tools for registry maintenance",
	classifiers=[
		"Development Status :: 4 - Beta",
		"Operating System :: POSIX",
		"Programming Language :: Python :: 3.3",
		"Topic :: Internet :: Log Analysis",
		"Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
		"Topic :: System :: Networking",
		"Topic :: System :: Systems Administration"
	],
	long_description=__doc__,
	install_requires=[
		"Jinja2==2.7.3",
		"bottle==0.12.8",
		"redis==2.10.3",
		"netaddr==0.7.13",
		"flynn==1.0.0b2"
	],
	entry_points={
		"console_scripts": [
			"lglass-regtool = lglass.tools.regtool:main",
			"lglass-roagen = lglass.tools.roagen:main",
			"lglass-rpsl = lglass.rpsl:main",
			"lglass-web = lglass.web.__main__:main",
			"lglass-whoisd = lglass.whoisd:main",
			"lglass-zonegen = lglass.tools.zonegen:main"
		]
	},
	package_data={
		"lglass": ["schemas/*"],
		"lglass.web": ["templates/*.html", "templates/**/*.html"]
	}
)

