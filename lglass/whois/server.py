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

class SimpleWhoisServer(object):
    version_string = "% lglass.whois.server {}\n".format(lglass.version).encode()
    not_found_template = "%ERROR:101: no entries found\n" + \
            "%\n" + "% No entries found in source {source}.\n\n"
    not_allowed_template = "%ERROR:102: not allowed\n\n"
    preamble_template = "% This is the {source} Database query service.\n" + \
            "% The objects are in RPSL format.\n\n"
    abuse_template = "% Abuse contact for '{object_key}' is '{contact}'\n"
    allow_inverse_search = False

    def __init__(self, engine):
        self.engine = engine
        self._sources = None

    @property
    def sources(self):
        if self._sources is None:
            return [self.database_name]
        return self._sources

    @sources.setter
    def sources(self, new_sources):
        self._sources = new_sources

    @property
    def preamble(self):
        if self.preamble_template is not None:
            return self.preamble_template.format(source=self.database_name)

    @preamble.setter
    def preamble(self, new_pre):
        self.preamble_template = new_pre

    @property
    def not_found_message(self):
        if self.not_found_template is not None:
            return self.not_found_template.format(source=self.database_name)

    @property
    def not_allowed_message(self):
        if self.not_allowed_template is not None:
            return self.not_allowed_template.format(source=self.database_name)

    @not_found_message.setter
    def not_found_message(self, new_nfm):
        self.not_found_template = new_nfm

    @property
    def database_name(self):
        return self.database.database_name

    @property
    def database(self):
        return self.engine.database

    def abuse_message(self, object_key, contact):
        return self.abuse_template.format(object_key=object_key, contact=contact)

    def _build_argparser(self):
        argparser = lglass.whois.engine.new_argparser(cls=SolidArgumentParser,
                add_help=False)
        argparser.add_argument("--persistent-connection", "-k",
                action="store_true", default=False)
        argparser.add_argument("--inverse", "-i")
        argparser.add_argument("-q")
        return argparser

    async def query(self, request, writer):
        argparser = self._build_argparser()
        args = argparser.parse_args(request.split())

        if args.q:
            if args.q == "version":
                writer.write(self.version_string)
            elif args.q == "types":
                writer.write("\n".join(sorted(self.database.object_classes)).encode())
                writer.write(b"\n\n")
            elif args.q == "sources":
                for source in self.sources:
                    writer.write(source.encode() + b":3:N:0-0\n")
                writer.write(b"\n")
            await writer.drain()
            return args.persistent_connection

        query_kwargs = lglass.whois.engine.args_to_query_kwargs(args)

        inverse_fields = None
        if args.inverse is not None:
            if not self.allow_inverse_search:
                if self.not_allowed_message:
                    writer.write(self.not_allowed_message.encode() + b"\n")
                await writer.drain()
                return args.persistent_connection
            inverse_fields = args.inverse.split(",")

        db = self.engine.new_query_database()
        for term in args.terms or []:
            if inverse_fields is not None:
                term = {f: term for f in inverse_fields}
            results = self.engine.query(term, database=db, **query_kwargs)
            writer.write(self.format_results(results,
                primary_keys=args.primary_keys,
                pretty_print_options={
                    "min_padding": 16,
                    "add_padding": 0},
                database=db).encode())

        writer.write(b"\n")
        await writer.drain()

        return args.persistent_connection

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

    def format_results(self, results, primary_keys=False,
            include_abuse_contact=True, pretty_print_options={},
            database=None):
        if not results and self.not_found_message is not None:
            return self.not_found_message
        response = ""
        for primary in sorted(results.keys(), key=lambda k: k.object_class):
            primary_key = self.database.primary_key(primary)
            related_objects = list(results[primary])[1:]
            if include_abuse_contact:
                abuse_contact = self.engine.query_abuse(primary,
                        database=database)
                if abuse_contact:
                    response += self.abuse_message(primary_key, abuse_contact)
                    response += "\n"
            if primary_keys:
                primary = primary.primary_key_object()
                response += "".join(primary.pretty_print(**pretty_print_options))
                response += "\n"
                continue
            response += "% Information related to '{}'\n\n".format(
                    self.database.primary_key(primary))
            response += "".join(primary.pretty_print(**pretty_print_options))
            response += "\n"
            for obj in related_objects:
                response += "".join(obj.pretty_print(**pretty_print_options))
                response += "\n"
        return response

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Simple whois server")
    argparser.add_argument("--port", "-p", default=4343)
    argparser.add_argument("--address", "-a", default="::1,127.0.0.1")
    argparser.add_argument("--preamble", "-P")
    argparser.add_argument("--sources")
    argparser.add_argument("--handle-hint")
    argparser.add_argument("database")

    args = argparser.parse_args()

    db = lglass.nic.FileDatabase(args.database)
    engine = lglass.whois.engine.WhoisEngine(db)
    server = SimpleWhoisServer(engine)

    if args.preamble is not None:
        with open(args.preamble) as fh:
            server.preamble = fh.read()
    
    if args.handle_hint is not None:
        engine.type_hints[args.handle_hint] = engine.handle_classes

    if args.sources is not None:
        server.sources = args.sources.split(",")

    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(server.handle, args.address.split(","), args.port, loop=loop)
    s = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    s.close()
    loop.run_until_complete(s.wait_closed())
    loop.close()

