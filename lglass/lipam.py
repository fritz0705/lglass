# coding: utf-8

import argparse
import asyncio
import itertools
import os
import subprocess
import sys
import tempfile

import netaddr

import lglass.nic
import lglass.whois.engine
import lglass.whois.server

from lglass.ipam import *


class IPAMTool(object):
    def __init__(self, stdin=None, stdout=None, stderr=None, editor=None):
        if stdin is None:
            stdin = sys.stdin
        if stdout is None:
            stdout = sys.stdout
        if stderr is None:
            stderr = sys.stderr
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        if editor is None:
            editor = os.getenv("EDITOR")
        self.editor = editor
        self.pretty_print_options = dict(
            min_padding=16,
            add_padding=0)
        self.argparser = argparse.ArgumentParser()
        self.argparser.add_argument("--database", "-D", default=".")
        self.argparser.add_argument("--verbose", "-v", action="store_true",
                                    default=False)
        self.argparser.add_argument('--editor')
        self.command_parsers = self.argparser.add_subparsers(dest="subcommand")
        # lipam add-inverse OBJECT...
        add_inverse_parser = self.command_parsers.add_parser("add-inverse")
        add_inverse_parser.add_argument("object", nargs="*")
        # lipam add-object OBJECT_CLASS OBJECT_KEY
        add_object_parser = self.command_parsers.add_parser('add-object',
                                                            aliases=["add"])
        add_object_parser.add_argument("file", nargs="*")
        # lipam create-address [--admin-c NIC-HDL] [--tech-c NIC-HDL]
        #                      [--add-host|--no-add-host] [--status STATUS]
        #                      [-h|--hostname HOSTNAME] ADDRESS
        create_address_parser = self.command_parsers.add_parser(
            "create-address")
        create_address_parser.add_argument("--admin-c", action="append",
                                           default=[])
        create_address_parser.add_argument("--tech-c", action="append",
                                           default=[])
        create_address_parser.add_argument("--hostname", "-H", action="append",
                                           default=[])
        create_address_parser.add_argument("--descr", "-D")
        create_address_parser.add_argument("--add-inverse", "-i",
                                           action="store_true", default=False)
        create_address_parser.add_argument(
            "--no-add-inverse",
            action="store_false",
            dest="add_inverse")
        create_address_parser.add_argument("--edit", action="store_true",
                                           default=True)
        create_address_parser.add_argument("--no-edit", action="store_false",
                                           dest="edit")
        create_address_parser.add_argument("--status", "-S")
        create_address_parser.add_argument("address")
        # lipam create-host [--admin-c NIC-HDL] [--tech-c NIC-HDL]
        #                   [-A|--address ADDRESS] [--l2-address|-2 LLADDR]
        #                   [--add-address|--no-add-address] [--edit|--no-edit]
        #                   [--status STATUS] HOSTNAME
        create_host_parser = self.command_parsers.add_parser("create-host")
        create_host_parser.add_argument("--admin-c", action="append",
                                        default=[])
        create_host_parser.add_argument("--tech-c", action="append",
                                        default=[])
        create_host_parser.add_argument("--descr", "-D")
        create_host_parser.add_argument("--address", "-A", action="append",
                                        default=[])
        create_host_parser.add_argument("--l2-address", "-2", action="append",
                                        default=[])
        create_host_parser.add_argument("--add-inverse", "-i",
                                        action="store_true", default=False)
        create_host_parser.add_argument(
            "--no-add-inverse",
            action="store_false",
            dest="add_inverse")
        create_host_parser.add_argument("--edit", action="store_true",
                                        default=True)
        create_host_parser.add_argument("--no-edit", action="store_false",
                                        dest="edit")
        create_host_parser.add_argument("--status", "-S")
        create_host_parser.add_argument("hostname")
        # lipam create-inetnum [--admin-c NIC-HDL] [--tech-c NIC-HDL]
        #                      [--descr DESCR] [--netname NAME] [--org ORG]
        #                      [--status STATUS] NETWORK
        create_inetnum_parser = self.command_parsers.add_parser(
            "create-inetnum")
        create_inetnum_parser.add_argument("--admin-c", action="append",
                                           default=[])
        create_inetnum_parser.add_argument("--tech-c", action="append",
                                           default=[])
        create_inetnum_parser.add_argument("--descr", "-D")
        create_inetnum_parser.add_argument("--status", "-S")
        create_inetnum_parser.add_argument("--netname", "-N")
        create_inetnum_parser.add_argument("--org", "-O")
        create_inetnum_parser.add_argument("--edit", action="store_true",
                                           default=True)
        create_inetnum_parser.add_argument("--no-edit", action="store_false",
                                           dest="edit")
        create_inetnum_parser.add_argument("network")
        # lipam create-object OBJECT_CLASS OBJECT_KEY
        create_object_parser = self.command_parsers.add_parser(
            "create-object", aliases=["create"])
        create_object_parser.add_argument(
            "--add", "-a", nargs=2, action="append", default=[])
        create_object_parser.add_argument("--admin-c", action="append",
                                          default=[])
        create_object_parser.add_argument("--tech-c", action="append",
                                          default=[])
        create_object_parser.add_argument("--edit", action="store_true",
                                          default=True)
        create_object_parser.add_argument("--no-edit", action="store_false",
                                          dest="edit")
        create_object_parser.add_argument("--template", action="store_true",
                                          default=False)
        create_object_parser.add_argument(
            "--no-template", action="store_false", dest="template")
        create_object_parser.add_argument("object_class")
        create_object_parser.add_argument("object_key", nargs="?")
        # lipam delete-object OBJECT_CLASS OBJECT_KEY
        delete_object_parser = self.command_parsers.add_parser(
            'delete-object', aliases=['delete', 'rm'])
        delete_object_parser.add_argument('object_class')
        delete_object_parser.add_argument('object_key')
        # lipam edit-object OBJECT_CLASS OBJECT_KEY
        edit_object_parser = self.command_parsers.add_parser('edit-object',
                                                             aliases=["edit"])
        edit_object_parser.add_argument('object_class')
        edit_object_parser.add_argument('object_key')
        # lipam format-object OBJECT
        format_object_parser = self.command_parsers.add_parser(
            "format-object", aliases=["format"])
        format_object_parser.add_argument("--object", "-o", nargs=2)
        format_object_parser.add_argument("object_class", nargs='?')
        format_object_parser.add_argument("object_key", nargs='?')
        # lipam generate-dns DOMAIN
        generate_dns_parser = self.command_parsers.add_parser('generate-dns')
        generate_dns_parser.add_argument('--delegate', action='store_true',
                                         default=True)
        generate_dns_parser.add_argument('--no-delegate', action='store_false',
                                         dest='delegate')
        generate_dns_parser.add_argument('--fqdn', action='store_true',
                                         default=True)
        generate_dns_parser.add_argument('--no-fqdn', action='store_false',
                                         dest='fqdn')
        generate_dns_parser.add_argument('--l2-address-rrtype', default='TXT')
        generate_dns_parser.add_argument('--ipv4', action='store_true',
                                         default=True)
        generate_dns_parser.add_argument('--no-ipv4', action='store_false',
                                         dest='ipv4')
        generate_dns_parser.add_argument('--ipv6', action='store_true',
                                         default=True)
        generate_dns_parser.add_argument('--no-ipv6', action='store_false',
                                         dest='ipv6')
        generate_dns_parser.add_argument('--ds', action='store_true',
                                         default=True)
        generate_dns_parser.add_argument('--no-ds', action='store_false',
                                         dest='ds')
        generate_dns_parser.add_argument('--glue', action='store_true',
                                         default=True)
        generate_dns_parser.add_argument('--no-glue', action='store_false',
                                         dest='glue')
        generate_dns_parser.add_argument(
            '--comments', "-C", action='store_true', default=False)
        generate_dns_parser.add_argument('--no-comments', action='store_false',
                                         dest='comments')
        generate_dns_parser.add_argument('--netname-rrtype', default='TXT')
        generate_dns_parser.add_argument('--netname', action='store_true',
                                         default=False)
        generate_dns_parser.add_argument('--no-netname', action='store_false',
                                         dest='netname')
        generate_dns_parser.add_argument(
            "--custom-records", action="store_true", default=True)
        generate_dns_parser.add_argument(
            "--no-custom-records",
            action="store_false",
            dest="custom_records")
        generate_dns_parser.add_argument("--exact", action="store_true",
                                         default=True)
        generate_dns_parser.add_argument(
            "--no-exact", "-X", action="store_false", dest="exact")
        generate_dns_parser.add_argument('domain')
        # lipam get-object OBJECT_CLASS OBJECT_KEY
        get_object_parser = self.command_parsers.add_parser('get-object',
                                                            aliases=['get'])
        get_object_parser.add_argument('object_class')
        get_object_parser.add_argument('object_key')
        # lipam lint
        lint_parser = self.command_parsers.add_parser('lint')
        lint_parser.add_argument('--object', '-o', action='append',
                                 default=[], nargs=2)
        lint_parser.add_argument('--warn-missing-inverse', action='store_true',
                                 default=True)
        lint_parser.add_argument(
            '--no-warn-missing-inverse',
            action='store_false',
            dest='warn_missing_inverse')
        lint_parser.add_argument('--warn-foreign-reference',
                                 action='store_true', default=True)
        lint_parser.add_argument(
            '--no-warn-foreign-reference',
            action='store_false',
            dest='warn_foreign_reference')
        lint_parser.add_argument('--warn-missing-object',
                                 action='store_true', default=True)
        lint_parser.add_argument(
            '--no-warn-missing-object',
            action='store_false',
            dest='warn_missing_object')
        lint_parser.add_argument('--warn-address-format',
                                 action='store_true', default=True)
        lint_parser.add_argument(
            '--no-warn-address-format',
            action='store_false',
            dest='warn_address_format')
        lint_parser.add_argument('--warn-wrong-mntner', action='store_true',
                                 default=True)
        lint_parser.add_argument(
            '--no-warn-wrong-mntner',
            action='store_false',
            dest='warn_wrong_mntner')
        lint_parser.add_argument('object_class', nargs='?')
        lint_parser.add_argument('object_key', nargs='?')
        # lipam list-network [--format|-F (table|objects)] [--types TYPES]
        #                    NETWORK
        list_network_parser = self.command_parsers.add_parser('list-network')
        list_network_parser.add_argument('--types', '-T',
                                         default='address,network')
        list_network_parser.add_argument(
            '--format',
            '-F',
            choices=[
                'table',
                'objects',
                'primary-keys',
                'primary',
                'keys'],
            default='keys')
        list_network_parser.add_argument("--hosts", "-H", action="store_true",
                                         default=False)
        list_network_parser.add_argument("--no-hosts", action="store_false",
                                         dest="hosts")
        list_network_parser.add_argument('network')
        # lipam rename-object object_class old_object_key new_object_key
        rename_object_parser = self.command_parsers.add_parser("rename-object",
                aliases=["rename", "move", "move-object"])
        rename_object_parser.add_argument("object_class")
        rename_object_parser.add_argument("old_object_key")
        rename_object_parser.add_argument("new_object_key")
        # lipam renumber old_ip_address new_ip_address
        renumber_parser = self.command_parsers.add_parser("renumber")
        renumber_parser.add_argument("old_ip_address")
        renumber_parser.add_argument("new_ip_address")
        # lipam whois ...
        whois_parser = self.command_parsers.add_parser('whois')
        lglass.whois.engine.new_argparser(whois_parser)
        # lipam whois-server
        whois_server_parser = self.command_parsers.add_parser('whois-server')
        whois_server_parser.add_argument("--port", "-p", default=4343)
        whois_server_parser.add_argument(
            "--address", "-a", default="::1,127.0.0.1")

    def main(self, argv=None):
        # parse cli arguments
        if argv is None:
            argv = sys.argv[1:]
        self.args = self.argparser.parse_args(argv)
        # initialize database
        self.database = FileDatabase(self.args.database)
        sc = self.args.subcommand
        if sc == "add-inverse":
            return self.add_inverse()
        elif sc in {"add-object", "add"}:
            return self.add_object()
        elif sc == "create-address":
            return self.create_address()
        elif sc == "create-host":
            return self.create_host()
        elif sc == "create-inetnum":
            return self.create_inetnum()
        elif sc in {"create-object", "create"}:
            return self.create_object()
        elif sc in {"delete-object", "delete"}:
            return self.delete_object()
        elif sc in {"edit-object", "edit"}:
            return self.edit_object()
        elif sc in {"format-object", "format"}:
            return self.format_object()
        elif sc == "generate-dns":
            return self.generate_dns()
        elif sc in {"get-object", "get"}:
            return self.get_object()
        elif sc == "lint":
            return self.lint()
        elif sc == "list-network":
            return self.list_network()
        elif sc in {"move", "move-object", "rename", "rename-object"}:
            return self.rename_object()
        elif sc == "whois":
            return self.whois()
        elif sc == "whois-server":
            return self.whois_server()
        else:
            self.argparser.print_usage()

    def add_object(self):
        objs = []
        if not self.args.file:
            objs.extend(lglass.object.parse_objects(sys.stdin.readlines()))
        else:
            for f in self.args.file:
                with open(f) as fh:
                    objs.extend(lglass.object.parse_objects(fh.readlines()))
        for obj in objs:
            self._save_object(obj)

    def add_inverse(self):
        objects = list(
            self.database.lookup(
                types={
                    "host",
                    "address"},
                keys=self.args.object))
        for object_class, object_key in objects:
            obj = self.database.fetch(object_class, object_key)
            if obj.object_class == "host":
                self._add_inverse_addresses(obj)
            elif obj.object_class == "address":
                self._add_inverse_hosts(obj)

    def _add_inverse_addresses(self, host):
        for address in host.get("address"):
            created = False
            try:
                address = self.database.fetch("address", address)
            except KeyError:
                address = self.database.create_object([("address", address)])
                created = True
            if host.object_key not in address.get("hostname"):
                address.append_group("hostname", host.object_key)
                if created:
                    address.extend(host.getitems("admin-c"))
                    address.extend(host.getitems("tech-c"))
                self._save_object(address)

    def _add_inverse_hosts(self, address):
        for hostname in address.get("hostname"):
            created = False
            try:
                host = self.database.fetch("host", hostname)
            except KeyError:
                host = self.database.create_object([("host", hostname)])
                created = True
            if str(address.ip_address) not in host.get("address"):
                host.append_group("address", str(address.ip_address))
                if created:
                    host.extend(address.getitems("admin-c"))
                    host.extend(address.getitems("tech-c"))
                self._save_object(host)

    def create_address(self):
        addr = netaddr.IPAddress(self.args.address)
        obj = self._new_object("address", addr)
        if self.args.descr:
            obj.append("descr", self.args.descr)
        obj.extend(("hostname", hostname) for hostname in self.args.hostname)
        obj.extend(("admin-c", admin_c) for admin_c in self.args.admin_c)
        obj.extend(("tech-c", tech_c) for tech_c in self.args.tech_c)
        if self.args.status:
            obj.append("status", self.args.status)
        if self.args.edit:
            obj = self._edit_object(obj)
        netaddr.IPAddress(obj.object_key)
        self._save_object(obj)
        if self.add_inverse:
            self._add_inverse_hosts(obj)

    def create_host(self):
        hostname = self.args.hostname
        obj = self._new_object("host", hostname)
        if self.args.descr:
            obj.append("descr", self.args.descr)
        obj.extend((("l2-address", address)
                    for address in self.args.l2_address), append_group=True)
        obj.extend((("address", address) for address in self.args.address),
                   append_group=True)
        obj.extend((("admin-c", admin_c) for admin_c in self.args.admin_c),
                   append_group=True)
        obj.extend((("tech-c", tech_c) for tech_c in self.args.tech_c),
                   append_group=True)
        if self.args.status:
            obj.append("status", self.args.status)
        if self.args.edit:
            obj = self._edit_object(obj)
        self._save_object(obj)
        if self.add_inverse:
            self._add_inverse_addresses(obj)

    def create_inetnum(self):
        net = netaddr.IPNetwork(self.args.network)
        obj = self._new_object("inetnum" if net.version == 4 else "inet6num",
                               net)
        if self.args.netname:
            obj.append("netname", self.args.netname)
        if self.args.descr:
            obj.append("descr", self.args.descr)
        if self.args.org:
            obj.append("org", self.args.obj)
        obj.extend((("admin-c", admin_c) for admin_c in self.args.admin_c),
                   append_group=True)
        obj.extend((("tech-c", tech_c) for tech_c in self.args.tech_c),
                   append_group=True)
        if self.args.status:
            obj.append("status", self.args.status)
        if self.args.edit:
            obj = self._edit_object(obj)
        self._save_object(obj)

    def create_object(self):
        obj = self._new_object(self.args.object_class, self.args.object_key,
                               template=self.args.template)
        obj.extend((("admin-c", admin_c) for admin_c in self.args.admin_c),
                   append_group=True)
        obj.extend((("tech-c", tech_c) for tech_c in self.args.tech_c),
                   append_group=True)
        obj.extend(((key, value) for key, value in self.args.add),
                   append_group=True)
        if self.args.edit:
            obj = self._edit_object(obj)
        self._save_object(obj)

    def delete_object(self):
        obj = self.database.fetch(self.args.object_class, self.args.object_key)
        self.database.delete(obj)

    def edit_object(self):
        obj = self.database.fetch(self.args.object_class, self.args.object_key)
        obj = self._edit_object(obj)
        obj.remove("last-modified")
        obj.remove("source")
        self._save_object(obj)

    def format_object(self):
        objs = []
        if self.args.object_class:
            if self.args.object_key:
                objs.append((self.args.object_class, self.args.object_key))
            else:
                objs.extend(
                    self.database.lookup(
                        types={
                            self.args.object_class}))
        if self.args.object:
            for obj in self.args.object:
                objs.append((obj[0], obj[1]))
        if not objs:
            objs = self.database.lookup()
        for object_class, object_key in objs:
            obj = self.database.fetch(object_class, object_key)
            self._save_object(obj)

    def generate_dns(self):
        db = self.database
        dom = lglass.dns.domain_split(self.args.domain)
        addresses = set()
        domains = set()
        hosts = set()
        inetnums = set()
        if self.args.delegate:
            domains = set(domain_name for _, domain_name
                          in db.lookup(types="domain")
                          if lglass.dns.is_subdomain(domain_name, dom) and
                          (self.args.exact or
                           not lglass.dns.domain_equal(domain_name, dom)))
        if self.args.fqdn:
            hosts = set(hostname for _, hostname in db.lookup(types="host")
                        if lglass.dns.is_subdomain(hostname, dom))
        if lglass.dns.is_reverse_domain(dom) or not dom:
            addresses = set(address for _, address
                            in db.lookup(types="address")
                            if lglass.dns.is_subdomain(
                                netaddr.IPAddress(address).reverse_dns, dom))
        for address in sorted(addresses):
            address = db.fetch("address", address)
            rdns_domain = address.ip_address.reverse_dns
            if self.args.comments:
                self.print("; address: {}".format(address.object_key))
            for hostname in address.hostnames:
                self.print("{rdns} PTR {hostname}.".format(
                    rdns=rdns_domain,
                    hostname=hostname))
        for domain in sorted(domains):
            domain = db.fetch("domain", domain)
            if self.args.comments:
                self.print("; domain: {}".format(domain.object_key))
            self.print(
                "\n".join(
                    lglass.dns.generate_delegation(
                        domain,
                        include_glue=self.args.glue,
                        include_ds=self.args.ds)))
            if self.args.custom_records:
                for rr in domain.get("rr"):
                    self.print("{hostname}. {rr}".format(
                        hostname=domain.object_key,
                        rr=rr))
        for host in sorted(hosts):
            host = db.fetch("host", host)
            if self.args.comments:
                self.print("; host: {}".format(host.object_key))
            for addr in host.addresses:
                addr = netaddr.IPAddress(addr)
                if addr.version == 4 and self.args.ipv4:
                    self.print("{hostname}. A {address}".format(
                        hostname=host.object_key,
                        address=addr))
                if addr.version == 6 and self.args.ipv6:
                    self.print("{hostname}. AAAA {address}".format(
                        hostname=host.object_key,
                        address=addr))
            for l2_address in host.l2_addresses:
                self.print("{hostname}. {rrtype} \"{address}\"".format(
                    hostname=host.object_key,
                    rrtype=self.args.l2_address_rrtype,
                    address=l2_address))
            if self.args.custom_records:
                for rr in host.get("rr"):
                    self.print("{hostname}. {rr}".format(
                        hostname=host.object_key,
                        rr=rr))

    def get_object(self):
        obj = self.database.fetch(self.args.object_class, self.args.object_key)
        self.print_object(obj)

    def lint(self):
        objs = []
        if self.args.object_class:
            if self.args.object_key:
                objs.append((self.args.object_class, self.args.object_key))
            else:
                objs.extend(
                    self.database.lookup(
                        types={
                            self.args.object_class}))
        if self.args.object:
            for obj in self.args.object:
                objs.append((obj[0], obj[1]))
        if not objs:
            objs = self.database.lookup()
        for object_class, object_key in objs:
            obj = self.database.fetch(object_class, object_key)

    def list_network(self):
        eng = self.whois_engine()
        net = netaddr.IPNetwork(self.args.network)
        ms = eng.query_more_specifics(net, levels=-1)
        if self.args.format == "objects":
            for res in ms:
                self.print_object(res)
                if res.object_class == "address" and self.args.hosts:
                    for host in self.database.find(types="host",
                                                   keys=res.get("hostname")):
                        self.print_object(host)
        elif self.args.format in {'primary', 'primary-keys', 'keys'}:
            for res in ms:
                self.print_object(res.primary_key_object())
                if res.object_class == "address" and self.args.hosts:
                    for host in self.database.find(types="host",
                                                   keys=res.get("hostname")):
                        self.print_object(host.primary_key_object())
        elif self.args.format == 'table':
            self.print_network_table(net, ms)

    def rename_object(self):
        obj = self.database.fetch(self.args.object_class,
                self.args.old_object_key)
        nobj = obj.copy()
        nobj.object_key = self.args.new_object_key
        try:
            self._save_object(nobj)
            self.database.delete(obj)
        except:
            try:
                self.database.delete(nobj)
            except:
                pass
            finally:
                self._save_object(obj)
            raise

    def whois(self):
        eng = self.whois_engine()
        query_kwargs = lglass.whois.engine.args_to_query_kwargs(self.args)
        for term in self.args.terms:
            results = eng.query(term, **query_kwargs)
            for primary in sorted(results.keys(), key=lambda k: k.type):
                primary_key = self.database.primary_key(primary)
                related_objects = list(results[primary])[1:]
                abuse_contact = eng.query_abuse(primary)
                if abuse_contact:
                    self.print("% Abuse contact for '{}' is '{}'".format(
                        primary_key, abuse_contact))
                    self.print()
                if self.args.primary_keys:
                    primary = primary.primary_key_object()
                    self.print_object(primary)
                    continue
                self.print("% Information related to '{}'".format(primary_key))
                self.print()
                self.print_object(primary)
                for obj in related_objects:
                    self.print_object(obj)

    def whois_server(self):
        server = lglass.whois.server.SimpleWhoisServer(self.whois_engine())
        loop = asyncio.get_event_loop()
        coro = asyncio.start_server(server.handle,
                                    self.args.address.split(","),
                                    self.args.port,
                                    loop=loop)
        s = loop.run_until_complete(coro)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        s.close()
        loop.run_until_complete(s.wait_closed())
        loop.close()

    def whois_engine(self):
        eng = lglass.whois.engine.WhoisEngine(self.database)
        eng.ipv4_more_specific_prefixlens = set(range(0, 33))
        eng.ipv6_more_specific_prefixlens = set(range(0, 129))
        eng.use_schemas = True
        return eng

    def _edit_object(self, obj):
        if not os.isatty(self.stdin.fileno()) or \
                not os.isatty(self.stdout.fileno()):
            return obj
        editor = self.editor
        if self.args.editor is not None:
            editor = self.args.editor
        with tempfile.NamedTemporaryFile("w+b", buffering=0) as fh:
            fh.write(
                "".join(
                    obj.pretty_print(
                        **self.pretty_print_options)).encode())
            fh.write("% Uncomment the next line to abort process\n".encode())
            fh.write("% abort:   abort\n".encode())
            fh.flush()
            argv = [editor, fh.name]
            subprocess.run(argv)
            fh.seek(0)
            obj = lglass.object.parse_object(fh.read().decode().splitlines())
        obj = self.database.create_object(obj)
        if "abort" in obj:
            raise Exception()
        return obj

    def _new_object(self, object_class, object_key, template=False):
        if object_key is None:
            object_key = "[" + object_class + "]"
        else:
            object_key = str(object_key)
        obj = self.database.create_object([(object_class, object_key)])
        if template:
            try:
                schema = lglass.schema.load_schema(self.database, object_class)
                obj.extend(schema.template())
            except KeyError:
                pass
        return obj

    def _save_object(self, obj, *args, **kwargs):
        kwargs = dict(kwargs)
        kwargs.update(self.pretty_print_options)
        if not isinstance(obj, lglass.object.Object):
            obj = self.database.create_object(obj)
        if self.args.verbose:
            self.print_object(obj)
        return self.database.save(obj, *args, **kwargs)

    def print_object(self, obj, *args, **kwargs):
        return self.print(
            "".join(
                obj.pretty_print(
                    **self.pretty_print_options)),
            *args,
            **kwargs)

    def print(self, *args, **kwargs):
        return print(*args, **kwargs, file=self.stdout)


def main():
    t = IPAMTool()
    t.main()


if __name__ == "__main__":
    main()
