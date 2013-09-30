Registry tool
=============

The registry tool is a simple tool for network registries. The DN42 registry
is a great example of it, because it's used in DN42 to register objects and
resources. It's similar to the RIPE database.

The registry tool allows you simple access to a complex registry structure. It
provides tools to create, edit, and delete objects, to validate some objects
or all objects, and to generate a ROA table from your registry.

Configuration
-------------

The configuration is done by the .lglassrc file. The registry tool will search
for that file on startup up to the mount point. It's a simple JSON configuration
file with information about the database storage.

At the moment, the only property is the database chain, which is similar to
other database chains, but it should not contain any caching layer.

