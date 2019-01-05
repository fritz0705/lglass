#!/bin/python
# coding: utf-8

import psycopg2.pool
import psycopg2.extensions

import logging

import lglass.whois.server
import lglass_sql.nic
import lipam.sql


class LoggingCursor(psycopg2.extensions.cursor):
    def execute(self, sql, args=None):
        logger = logging.getLogger('sql_debug')
        logger.info(self.mogrify(sql, args).decode())

        try:
            psycopg2.extensions.cursor.execute(self, sql, args)
        except Exception as exc:
            logger.error("{}: {}".format(exc.__class__.__name__,
                                         exc))
            raise


logger = logging.getLogger('sql_debug')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

ripe = lglass_sql.nic.NicDatabase(
    psycopg2.pool.ThreadedConnectionPool(1, 10, "dbname=ripe",
                                         cursor_factory=LoggingCursor))

eng = lglass.whois.engine.WhoisEngine()
server = lglass.whois.server.SimpleWhoisServer(
    eng, [ripe],
    default_sources=["RIPE"])

lglass.whois.server.run_server(server, ["::", "0.0.0.0"], 4343)
