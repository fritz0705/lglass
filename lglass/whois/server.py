# coding: utf-8

import argparse
import asyncio

import lglass
import lglass.whois.engine
import lglass.nic


class SolidArgumentParser(argparse.ArgumentParser):
    def exit(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class Base(object):
    def __init__(self, engine, databases):
        self.databases = list(databases)
        self.engine = engine

    @property
    def sources(self):
        return [db.database_name for db
                in self.databases]

    @property
    def primary_database(self):
        return self.databases[0]


class SimpleWhoisServer(Base):
    version_string = "% lglass.whois.server {}\n".format(
        lglass.version).encode()
    not_found_template = "%ERROR:101: no entries found\n" + \
        "%\n" + "% No entries found in source {sources}.\n\n"
    not_allowed_template = "%ERROR:201: access denied\n\n"
    preamble_template = "% This is the {source} Database query service.\n" + \
        "% The objects are in RPSL format.\n\n"
    abuse_template = "% Abuse contact for '{object_key}' is '{contact}'\n"
    allow_inverse_search = True

    def __init__(self, engine, databases, default_sources=None):
        self.databases = list(databases)
        if default_sources is None:
            default_sources = [self.primary_database.database_name]
        self.default_sources = default_sources
        self.engine = engine

    @property
    def preamble(self):
        if self.preamble_template is not None:
            return self.preamble_template.format(
                source=self.primary_database.database_name)

    @preamble.setter
    def preamble(self, new_pre):
        self.preamble_template = new_pre

    def not_found_message(self, databases):
        if self.not_found_template is not None:
            return self.not_found_template.format(
                sources=",".join(db.database_name for db in databases))

    @property
    def not_allowed_message(self):
        if self.not_allowed_template is not None:
            return self.not_allowed_template.format(
                source=self.primary_database.database_name)

    def abuse_message(self, object_key, contact):
        return self.abuse_template.format(
            object_key=object_key, contact=contact)

    def _build_argparser(self):
        argparser = lglass.whois.engine.new_argparser(
            cls=SolidArgumentParser, add_help=False, prog="whois")
        argparser.add_argument("--persistent-connection", "-k",
                               action="store_true", default=False,
                               help=argparse.SUPPRESS)
        argparser.add_argument(
            "--inverse",
            "-i",
            help="do an inverse look-up for specified ATTRibutes")
        argparser.add_argument("-q", help="query specified server info",
                               choices=["version", "types", "sources"])
        argparser.add_argument("-s", "--sources",
                               help="search the database mirrored from SOURCE")
        argparser.add_argument("-a", action="store_true", default=False,
                               help="search in all sources")
        argparser.add_argument("--template", "-t",
                               help="request template for object of TYPE")
        argparser.add_argument("--help", "-h", action="store_true",
                               help="display this help")
        argparser.add_argument("--client-address", action="store_true",
                help="perform query for client ip address")
        return argparser

    async def query(self, request, writer):
        argparser = self._build_argparser()
        try:
            args = argparser.parse_args(request.split())
        except:
            await writer.drain()
            return False

        if args.q:
            if args.q == "version":
                writer.write(self.version_string)
            elif args.q == "types":
                writer.write(
                    "\n".join(
                        sorted(
                            self.primary_database.object_classes)).encode())
                writer.write(b"\n\n")
            elif args.q == "sources":
                for source in self.sources:
                    writer.write(source.encode() + b":3:N:0-0\n")
                writer.write(b"\n")
            await writer.drain()
            return args.persistent_connection
        elif args.template is not None:
            return args.persistent_connection
        elif args.help:
            writer.write(
                self.format_comment(
                    argparser.format_help()).encode() +
                b"\n")
            await writer.drain()
            return args.persistent_connection

        if args.a:
            databases = self.databases
        else:
            if args.sources:
                sources = args.sources.upper().split(",")
            else:
                sources = self.default_sources
            databases = [db for db
                         in self.databases
                         if db.database_name in sources]

        if args.client_address:
            terms = [writer.get_extra_info('peername')[0]]
            writer.write("% Your client IP address is {}\n\n".format(terms[0]).encode())
        else:
            terms = args.terms
        if args.inverse:
            inverse_fields = args.inverse.split(",")
            terms = [(inverse_fields, (term.replace("_", " "),))
                    for term in terms]

        query_kwargs = lglass.whois.engine.args_to_query_kwargs(args)
        found_any = False

        for database in databases:
            results = self.perform_query(database, terms, args,
                                         query_kwargs, writer)
            if results:
                found_any = True
                if not args.inverse:
                    break

        if not found_any:
            writer.write(self.not_found_message(databases).encode())

        writer.write(b"\n")
        await writer.drain()

        return args.persistent_connection

    def send_results(self, writer, results, primary_keys=False,
                     include_abuse_contact=True, pretty_print_options={},
                     database=None):
        n = 0
        for role, obj in results:
            n += 1
            primary_key = database.primary_key(obj)
            if role == 'primary' and include_abuse_contact:
                abuse_contact = self.engine.query_abuse(obj,
                                                        database=database)
                if abuse_contact:
                    writer.write(self.abuse_message(primary_key,
                                                    abuse_contact).encode())
                    writer.write(b"\n")
            if role == 'primary' and primary_keys:
                writer.write("".join(obj.primary_key_object().pretty_print(
                    **pretty_print_options)).encode())
                writer.write(b"\n")
                continue
            elif role == 'related' and primary_keys:
                continue
            elif role == 'primary':
                writer.write("% Information related to '{}'\n\n".format(
                    primary_key).encode())

            writer.write(
                "".join(
                    obj.pretty_print(
                        **pretty_print_options)).encode())
            writer.write(b"\n")
        return n

    def perform_query(self, database, terms, query_args, query_kwargs, writer):
        database = self.engine.new_query_database(database)
        try:
            for term in terms:
                # Replace underscore by spaces
                if not isinstance(term, tuple):
                    term = term.replace("_", " ")
                results = self.engine.query_lazy(
                    term,
                    database=database,
                    **query_kwargs)
                return self.send_results(writer,
                                  results,
                                  primary_keys=query_args.primary_keys,
                                  pretty_print_options={
                                      "min_padding": 16,
                                      "add_padding": 0},
                                  database=database)
        finally:
            if hasattr(database, "close"):
                database.close()

    async def handle_persistent(self, reader, writer):
        while True:
            if self.preamble is not None:
                writer.write(self.preamble.encode())
            request = await reader.readline()
            request = request.decode()
            k = await self.query(request, writer)
            if k:
                break

    async def handle(self, reader, writer):
        if self.preamble is not None:
            writer.write(self.preamble.encode())
        request = await reader.readline()
        request = request.decode()
        persistent_connection = await self.query(request, writer)
        if persistent_connection:
            await self.handle_persistent(reader, writer)
        await writer.drain()
        writer.close()

    def format_comment(self, comment):
        res = ""
        for line in comment.splitlines():
            res += "% " + line + "\n"
        return res


def main(args=None, database_cls=lglass.nic.FileDatabase,
         server_cls=SimpleWhoisServer,
         engine_cls=lglass.whois.engine.WhoisEngine):
    argparser = argparse.ArgumentParser(description="Simple whois server")
    argparser.add_argument("--port", "-p", default=4343)
    argparser.add_argument("--address", "-a", default="::1,127.0.0.1")
    argparser.add_argument("--preamble", "-P")
    argparser.add_argument("--sources")
    argparser.add_argument("--handle-hint")
    argparser.add_argument("databases", nargs="+")

    if args is None:
        import sys
        args = sys.argv[1:]

    args = argparser.parse_args(args=args)

    databases = []
    for db in args.databases:
        databases.append(database_cls(db))

    engine = engine_cls()
    server = server_cls(engine, databases)

    if args.preamble is not None:
        with open(args.preamble) as fh:
            server.preamble = fh.read()

    if args.handle_hint is not None:
        engine.type_hints[args.handle_hint] = engine.handle_classes

    if args.sources is not None:
        server.sources = args.sources.split(",")

    run_server(server, args.address.split(","), args.port)


def run_server(server, addresses, port):
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(
        server.handle,
        addresses,
        port,
        loop=loop)
    s = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    s.close()
    loop.run_until_complete(s.wait_closed())
    loop.close()


if __name__ == "__main__":
    main()
