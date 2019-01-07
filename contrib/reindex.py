#!/bin/python
# coding: utf-8

import signal
import argparse
from datetime import datetime

argparser = argparse.ArgumentParser()
argparser.add_argument("--database-type", "-T", choices=["nic", "ipam"],
        default="nic")
argparser.add_argument("database")
args = argparser.parse_args()

if args.database_type == "nic":
    import lglass_sql.nic
    db = lglass_sql.nic.NicDatabase(args.database)
elif args.database_type == "ipam":
    import lipam.sql
    db = lipam.sql.IPAMDatabase(args.database)

n = 0
start = datetime.now()

def sigusr1(*args):
    global n
    print("Processed {} objects in {}".format(n, datetime.now() - start))

signal.signal(signal.SIGUSR1, sigusr1)

with db.session() as sess:
    for obj in sess.find():
        n += 1
        sess.reindex(obj)
    sess.commit()
