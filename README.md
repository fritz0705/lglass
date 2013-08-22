lglass
======

lglass is a collection of code and data files written in Python. It is designed
to support registries in their work and to provide public services for access
to the database.

It features

* a Whois server with a few RIPE flags
* a zonefile generator
* a (non-validating) ROA table generator
* a RPSL formatter
* a simple web interface

Most features are experimental and not stable at the moment.

Whois Server
------------

The Whois Server uses asyncore to operate asynchronously. It can serve
information from different data stores, like Redis, SQLite3 and the file system. 

The configuration file describes the data sources by using URLs, which refer
to lglass databases:

    {
    	"listen.host": "::",
    	"listen.port": 43,
    	"listen.protocol": 6,
    
    	"database": [
    		"lglass.database.file.FileDatabase:./",
    		"lglass.database.cidr.CIDRDatabase:",
    		"lglass.database.schema.SchemaDatabase:?types-include=person,aut-num",
    		"lglass.database.cache.CachedDatabase:"
    	]
    }

In this case, the whois server listens on any address on port 43, and serves
information from a filesystem database. It also provides range lookups for
single IP addresses and AS numbers. Furthermore, related objects are also
included and everything is cached in memory.

You can start the whois server by using

    $ ./bin/lglass-whoisd -c whoisd.cfg

It's possible to flush the caches by sending SIGUSR1 to the process.

Zonefile Generator
------------------

The zonefile generator is able to create DNS zones from registry for forward
DNS, and reverse DNS for IPv4 and IPv6.

You can generate a simple forward zonefile by calling

    $ ./bin/lglass-zonegen -d $DB -n ns1.example.org -n ns2.example.org -e admin.example.org dns -z dn42

This generates a zonefile for the `dn42.` zone, with ns1.example.org as master
nameserver and ns2.example.org as slave nameserver. The data is provided by
the file system database located at `$DB`.

The usage for reverse DNS is similar:

    $ ./bin/lglass-zonegen -d $DB -n ns1.example.org -n ns2.example.org -e admin.example.org rdns4 -N 172.22.0.0/16
    $ ./bin/lglass-zonegen -d $DB -n ns1.example.org -n ns2.exmaple.org -e admin.example.org rdns6 -N fd00::/8

The first will generate a zonefile for `22.172.in-addr.arpa`, and the second
for `d.f.ip6.arpa`.

ROA table Generator
-------------------

The ROA table generator produces input for birdc.

