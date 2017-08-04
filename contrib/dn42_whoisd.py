#!/bin/python
# coding: utf-8

import argparse
import asyncio

import lglass.dn42
import lglass.whois.engine
import lglass.whois.server

def create_database(db_path):
    return lglass.dn42.DN42Database(db_path)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="DN42 Whois server")
    argparser.add_argument("--port", "-p", default=4343)
    argparser.add_argument("--address", "-a", default="::1,127.0.0.1")
    argparser.add_argument("database")

    args = argparser.parse_args()

    db = create_database(args.database)
    engine = lglass.whois.engine.WhoisEngine(db)
    engine.type_hints[r"[0-9A-Za-z]+-DN42$"] = {"role", "person"}
    server = lglass.whois.server.SimpleWhoisServer(engine)

    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(server.handle, args.address.split(","),
            args.port, loop=loop)
    s = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        s.close()
    loop.run_until_complete(s.wait_closed())
    loop.close()

