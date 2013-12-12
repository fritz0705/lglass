Databases
=========

lglass has several database backends for persisting and accessing the registry
objects. The API is consistent through the several database backends. At the
moment the following database backends are supported:

* SQLite3
* Filesystem

SQLite3
-------

The SQLite3 database is really simple designed and not very performant.
Furthermore, its database schema is completely broken but it uses less memory
than our Filesystem database.

::

  whois+lglass.database.sqlite3+sqlite3:{PATH}

Filesystem
----------

The Filesystem database is our original database implementation and uses
directories to represent the object type while using the filename to represent
the primary key. Using this schema it is simple to use by humans but also
performant.

::

  whois+lglass.database.file+file:{PATH}

Pseudo databases
----------------

lglass also provides many pseudo databases which wraps around existing real
databases and provide additional information like inverse related objects and
IP range lookups. At the moment, there are two important pseudo databases:

* CIDR Database
* Schema Database

CIDR Database
~~~~~~~~~~~~~

The CIDR Database resolves requests for IP addresses and ASNs. It transforms
the request to a request for all possible supernets (cidr requests) and ranges
(range requests), and therefore returns also supernets and ranges.

::

  whois+lglass.database.cidr+cidr:?{params}

Possible parameters are:

+----------------+------------------------------------------------------------+
| Parameter      | Description                                                |
+================+============================================================+
| range-slice    | Python slice expression to slice the range request results |
+----------------+------------------------------------------------------------+
| cidr-slice     | Python slice expression to slice the cidr request results  |
+----------------+------------------------------------------------------------+

Schema Database
~~~~~~~~~~~~~~~

The Schema Database provides schema validation and inverse relation resolution.

::

  whois+lglass.database.schema+schema:?{params}

Possible parameters are:

+----------------+------------------------------------------------------------+
| Parameter      | Description                                                |
+================+============================================================+
| types-include  | Comma-separated list of types for inverse relation         |
|                | resolution                                                 |
+----------------+------------------------------------------------------------+

