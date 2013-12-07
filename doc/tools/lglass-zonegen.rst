:program:`lglass-zonegen` – Zonefile generator
==============================================

The :program:`lglass-zonegen` tool is a full-featured zone file generator. It
generates RFC-conform DNS zones for forward and reverse DNS delegations and
supports IPv4 and IPv6.

You have to give at least one `--nameserver` argument, exactly one `--master`
argument, and exactly one `--email` argument for your SOA email address.
Furthermore, you can use the `--database` argument for specifying the database
basepath.

::

  usage: lglass-zonegen [-h] [--database DATABASE] [--nameserver NAMESERVERS]
                        [--master MASTER] --email EMAIL [--ttl TTL]
                        {dns,rdns4,rdns6} ...

  Generator for delegating zones

  positional arguments:
    {dns,rdns4,rdns6}

  optional arguments:
    -h, --help            show this help message and exit
    --database DATABASE, --db DATABASE, -d DATABASE
                          Whois database
    --nameserver NAMESERVERS, -n NAMESERVERS
                          Nameserver
    --master MASTER, -m MASTER
                          Master nameserver
    --email EMAIL, -e EMAIL
                          Email address for SOA
    --ttl TTL, -t TTL     Time to live for generated zone

Forward Zones
-------------

To generate forward delegating zones (e.g. normal tld zone) you have to use the
`dns` subcommand. You have to give the `--zone` argument with the DNS zone as
argument. The output will be a valid DNS zone.

::
  
  usage: lglass-zonegen dns [-h] --zone ZONE

  optional arguments:
    -h, --help            show this help message and exit
    --zone ZONE, -z ZONE  DNS Zone

Example:

::

  # Generates the dn42 TLD zone including glue records
  $ lglass-zonegen -n ns1.fritz.dn42 -n ns2.fritz.dn42 -m ns1.fritz.dn42 \
    -e fritz.grimpen.net dns -z dn42

Reverse Zones
-------------

To generate reverse delegating zones (RDNS zones) you have to use either the
`rdns4` or the `rdns6` subcommand for IPv4 respectively IPv6.

IP version 4
~~~~~~~~~~~~

If you are using the `rdns4` command then you have to give the network via
argument `--network`. The network has to be a /8, /16, or /24.

::
  
  usage: lglass-zonegen rdns4 [-h] [--network NETWORK]

  optional arguments:
    -h, --help            show this help message and exit
    --network NETWORK, -N NETWORK
                          IPv4 Network

Example:

::
  
  # Generates the 172.22.0.0/16 rDNS zone
  $ lglass-zonegen -n ns1.fritz.dn42 -n ns2.fritz.dn42 -m ns1.fritz.dn42 \
    -e fritz.grimpen.net rdns4 -N 172.22.0.0/16
  # Generates the 172.23.0.0/16 rDNS zone
  $ lglass-zonegen -n ns1.fritz.dn42 -n ns2.fritz.dn42 -m ns1.fritz.dn42 \
    -e fritz.grimpen.net rdns6 -N 172.23.0.0/16

IP version 6
~~~~~~~~~~~~

If you are using the `rdns6` command then you have to give the network via
the argument `--network`, where the network has to be a valid IPv6 prefix.

:: 

  usage: lglass-zonegen rdns6 [-h] [--network NETWORK]

  optional arguments:
    -h, --help            show this help message and exit
    --network NETWORK, -N NETWORK
                          IPv6 Network

Example:

::

  # Generates the fd00::/8 rDNS zone
  $ lglass-zonegen -n ns1.fritz.dn42 -n ns2.fritz.dn42 -m ns1.fritz.dn42 \
    -e fritz.grimpen.net rdns6 -N fd00::/8

