:program:`lglass-bird` – Routing table export for BIRD
======================================================

:program:`lglass-bird` is a simple software tool written for routing table
exports from BIRD. It exports the routing table to the internal lglass CBOR
or JSON representation.

::

  usage: lglass-bird [-h] [-4] [-6] [-b BIRDC] [-f {json,cbor}] [-t TABLE]
                     [-p PROTOCOL]

  optional arguments:
    -h, --help            show this help message and exit
    -4
    -6
    -b BIRDC, --birdc BIRDC
                          Path to birdc executable
    -f {json,cbor}, --format {json,cbor}
                          Output format
    -t TABLE, --table TABLE
                          Routing table to export
    -p PROTOCOL, --protocol PROTOCOL
                          Protocol to export


