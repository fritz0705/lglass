# coding: utf-8

import argparse
import asyncio

import lglass.whois.engine
import lglass.nic

class SolidArgumentParser(argparse.ArgumentParser):
    def exit(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass

class SimpleWhoisServer(object):
    def __init__(self, engine, primer=None):
        self.engine = engine
        self.primer = primer

    @property
    def database(self):
        return self.engine.database

    def _build_argparser(self):
        argparser = SolidArgumentParser(add_help=False)
        argparser.add_argument("--domains", "-d", action="store_true", default=False)
        argparser.add_argument("--types", "-T")
        argparser.add_argument("--levels", "-l", type=int, default=0)
        argparser.add_argument("--exact", "-x", action="store_true", default=False)
        argparser.add_argument("--no-recurse", "-r", action="store_true", default=False)
        argparser.add_argument("--primary-keys", "-K", action="store_true", default=False)
        argparser.add_argument("terms", nargs="+")
        return argparser

    async def handle(self, reader, writer):
        if self.primer is not None:
            writer.write(self.primer.encode())

        request = await reader.readline()

        request = request.decode()
        argparser = self._build_argparser()
        args = argparser.parse_args(request.split())

        classes = args.types.split(",") if args.types \
                else self.database.object_classes

        query_args = dict(
                reverse_domain=args.domains,
                classes=classes,
                less_specific_levels=args.levels,
                exact_match=args.exact,
                recursive=not args.no_recurse)

        if args.primary_keys: query_args["recursive"] = False

        for term in args.terms or []:
            results = self.engine.query(term, **query_args)
            writer.write(self.format_results(results,
                primary_keys=args.primary_keys,
                pretty_print_options={
                    "min_padding": 16,
                    "add_padding": 0}).encode())

        writer.close()

    def format_results(self, results, primary_keys=False,
            include_abuse_contact=True, pretty_print_options={}):
        response = ""
        for primary in sorted(results.keys(), key=lambda k: k.object_class):
            primary_key = self.database.primary_key(primary)
            related_objects = list(results[primary])[1:]
            if include_abuse_contact:
                abuse_contact = self.engine.query_abuse(primary)
                if abuse_contact:
                    response += "% Abuse contact for '{}' is '{}'\n\n".format(
                            primary_key, abuse_contact)
            if primary_keys:
                response += "{}: {}\n\n".format(primary.object_class, primary_key)
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
    argparser.add_argument("--primer", "-P")
    argparser.add_argument("database")

    args = argparser.parse_args()

    db = lglass.nic.FileDatabase(args.database)
    engine = lglass.whois.engine.WhoisEngine(db)
    server = SimpleWhoisServer(engine)

    if args.primer is not None:
        with open(args.primer) as fh:
            server.primer = fh.read()

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
