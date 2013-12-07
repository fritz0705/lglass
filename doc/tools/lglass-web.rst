:program:`lglass-web` – Simple registry and routing web interface
=================================================================

The :program:`lglass-web` tool starts a simple HTTP server for the integrated
lglass web interface. It reads the configuration from a JSON file. Please
notice that the used web server is not suited for usage in public setups.
Default port is 8080.

::

  usage: lglass-web [-h] [--host HOST] [--port PORT] [--config CONFIG]

  Simple HTTP sevrer for lglass web interface

  optional arguments:
    -h, --help            show this help message and exit
    --host HOST, -H HOST  Bind to host
    --port PORT, -P PORT  Bind to port
    --config CONFIG, -c CONFIG
                          Path to configuration file
