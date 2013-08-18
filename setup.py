#!/usr/bin/env python3

import setuptools

with open("README.md") as f:
	long_description = f.read()

setuptools.setup(
	name="lglass",
	version="1.0dev",
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
		"netaddr>=0.7.10",
		"bottle>=0.11.6",
		"Jinja2>=2.7",
		"MarkupSafe>=0.18"
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

