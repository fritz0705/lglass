#!/bin/python
# coding: utf-8

import argparse
import sys
import signal
import traceback
import datetime

import lglass.object

import lglass_sql.nic

def objects(lines):
    obj = []
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode("iso-8859-15")
        if not line.strip() and obj:
            yield lglass.object.parse_object(obj)
            obj = []
        elif line[0] in {'%', '#'} or not line.strip():
            continue
        else:
            obj.append(line)
    if obj:
        yield lglass.object.parse_object(obj)

argparser = argparse.ArgumentParser()
argparser.add_argument("--schema", "-s")
argparser.add_argument("--encoding", "-e", default="iso-8859-15")
argparser.add_argument("database")

args = argparser.parse_args()

database = lglass_sql.nic.NicDatabase(args.database, schema=args.schema)

if hasattr(database, "session"):
    session = database.session()
else:
    session = database
print("Collecting local objects...", end='', flush=True)
current_objects = set(session.all_ids())
print(" Done.")

stats = dict(created=0,
        updated=0,
        deleted=0,
        ignored=0,
        start=datetime.datetime.now())

def report():
    global stats
    global current_objects
    print("Created {} / Updated {} / Deleted {} / "
            "Ignored {} objects in {}".format(stats["created"],
                stats["updated"],
                stats["deleted"],
                stats["ignored"],
                datetime.datetime.now() - stats["start"]))
    print("{} objects left".format(len(current_objects)))

signal.signal(signal.SIGUSR1, lambda *args: report())

print("Creating or updating local objects...", end='', flush=True)
for obj in objects(sys.stdin.buffer):
    try:
        obj = database.create_object(obj)
        spec = database.primary_spec(obj)
        try:
            local_obj = session.fetch(*spec)
        except KeyError:
            session.save(obj)
            stats["created"] += 1
            continue
        if local_obj.sql_id in current_objects:
            current_objects.remove(local_obj.sql_id)
        if local_obj == obj:
            stats["ignored"] += 1
            continue
        session.save(obj)
        stats["updated"] += 1
    except Exception as e:
        print("Error at object {!r}".format(obj))
        traceback.print_exc()
        stats["ignored"] += 1
print("Done")

print("Deleting local objects...", end='', flush=True)
for id_ in current_objects:
    try:
        session.delete_by_id(id_)
        stats["deleted"] += 1
    except Exception as e:
        traceback.print_exc(e)
        stats["ignored"] += 1
if hasattr(session, "commit"):
    session.commit()
if hasattr(session, "close"):
    session.close()
print("Done")

report()
