:program:`lglass-whoisd` – Full-featured whois server
=====================================================

The :program:`lglass-whoisd` tool starts the full-featured lglass whois server.
The configuration file is specified by the `--config` command line argument. By
default, the whois server will listen on both IPv4 and IPv6 on port 4343.

::

  usage: lglass-whoisd [-h] [--config CONFIG]

  Simple whois server

  optional arguments:
    -h, --help            show this help message and exit
    --config CONFIG, -c CONFIG
                          Path to configuration file

Configuration
-------------

The configuration file format is JSON and allows configuration of the database
chain, the listen parameters, the custom messages and the process management.

+-------------+---------------------------------------------------------------+
| Option      | Meaning                                                       |
+=============+===============================================================+
| listen.host | IP address for listening socket (Default: ::)                 |
+-------------+---------------------------------------------------------------+
| listen.port | TCP port for listening socket (Default: 4343)                 |
+-------------+---------------------------------------------------------------+
| listen.pro\ | Protocol for listening socket (4 or 6, by default 6)          |
| tocol       |                                                               |
+-------------+---------------------------------------------------------------+
| database    | Array of database URLs to initialize database chain           |
|             |                                                               |
|             | Default chain:                                                |
|             | ::                                                            |
|             |                                                               |
|             |   [                                                           |
|             |     "whois+lglass.database.file+file:.",                      |
|             |     "whois+lglass.database.cidr+cidr:",                       |
|             |     "whois+lglass.database.schema+schema:",                   |
|             |     "whois+lglass.database.cache+cached:"                     |
|             |   ]                                                           |
+-------------+---------------------------------------------------------------+
| database.t\ | Array of object types in database (Default: undefined)        |
| ypes        |                                                               |
+-------------+---------------------------------------------------------------+
| messages.p\ | String preamble for whois responses                           |
| reamble     |                                                               |
+-------------+---------------------------------------------------------------+
| messages.h\ | String help message for help requests                         |
| elp         |                                                               |
+-------------+---------------------------------------------------------------+
| process.us\ | User to change after initialization                           |
| er          |                                                               |
+-------------+---------------------------------------------------------------+
| process.gr\ | Group to change after initialization                          |
| oup         |                                                               |
+-------------+---------------------------------------------------------------+
| process.pi\ | Path to PID file                                              |
| dfile       |                                                               |
+-------------+---------------------------------------------------------------+

