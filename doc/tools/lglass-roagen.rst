:mod:`lglass-roagen` – ROA table generator
==========================================

`lglass-roagen` provides a really simple ROA table generator for BIRD Internet
Routing Daemon. It is capable of generating ROA tables for IPv4 and IPv6 from
a registry database, but doesn't validate the authenticity of the database.

::

  usage: lglass-roagen [-h] [--database DATABASE] [--table TABLE] [--flush] [-6]
                       [-4]

  Generator for ROA tables

  optional arguments:
    -h, --help            show this help message and exit
    --database DATABASE, -D DATABASE
                          Path to database
    --table TABLE, -t TABLE
                          Name of ROA table
    --flush, -f           Flush table entries before insertion
    -6                    Generate IPv6 ROA table
    -4                    Generate IPv4 ROA table

