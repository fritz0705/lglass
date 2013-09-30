lglass Whois Daemon
===================

The lglass whois daemon is implemented as part of the lglass main package
and provides whois services for IPv4 and IPv6 hosts. It was written using
asyncore and asyncloop in Python and supports multiple clients per
instance. It has no inetd mode at the moment.

Configuration
-------------

The configuration is done by a JSON file, which contains information
about the database chain and the protocol parameters:

+-------------------+-------------------------------------------------------+
| Parameter         | Description                                           |
+===================+=======================================================+
| listen.host       | Local IP address                                      |
+-------------------+-------------------------------------------------------+
| listen.port       | Local UDP port (default: 4343)                        |
+-------------------+-------------------------------------------------------+
| listen.protocol   | IP protocol version to use (4 for IPv4, 6 for IPv6)   |
+-------------------+-------------------------------------------------------+
| database          | Chain of databases                                    |
+-------------------+-------------------------------------------------------+
| messages.preamble | Preamble of response                                  |
+-------------------+-------------------------------------------------------+
| process.user      | User to drop priviliges after binding                 |
+-------------------+-------------------------------------------------------+
| process.group     | Group to drop priviliges after binding                |
+-------------------+-------------------------------------------------------+
| process.pidfile   | File to write PID after startup                       |
+-------------------+-------------------------------------------------------+

The chain of databases is a JSON array of URLs, which should define
databases. The first database must be a external database which pulls the
information from an external source. The other databases should be
layering databases which can cache and load further information.

Best practices
--------------

I recommend the usage of at least one caching layer on a public whois
server, the best caching is provided by the Redis database, which supports
cache expiration after some time and on request, but it's also possible to 
use the in-memory caching database. The latter one requires manual flushing.

Furthermore it's useful to use a CIDR lookup database to response to single
IP requests, e.g. returning 1.0.0.0/8 for 1.2.3.4. This is really useful
for other people while they're debugging their network and they see foreign
IP addresses. It also provides simple as-range lookup for ASN.

The schema filter is useful if you want to display inverse objects. Inverse
objects are objects which are related to another object in the registry and
it's possible to return some of them on request. Also a simple mechanism for
humans, because the aut-num object for route objects will be returned on
request.

