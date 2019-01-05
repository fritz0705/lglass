#!/bin/python
# coding: utf-8

# This script synchronizes a database from a GRS export by adding and updating
# the objects from the export, and comparing the occuring objects and
# subsequently deleting of the objects, which don't occur in the export but in
# the database.

import sys
import signal
import traceback
import time

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

database = lglass_sql.nic.NicDatabase("dbname=ripe-db")

if hasattr(database, "session"):
    session = database.session()
else:
    session = database
print("Collecting local objects...", end='', flush=True)
current_objects = set(session.lookup())
print(" Done.")

stats = dict(created=0,
        updated=0,
        deleted=0,
        ignored=0,
        start=time.time())

def report():
    global stats
    print("Created {} / Updated {} / Deleted {} / "
            "Ignored {} objects in {} seconds".format(stats["created"],
                stats["updated"],
                stats["deleted"],
                stats["ignored"],
                time.time() - stats["start"]))

signal.signal(signal.SIGUSR1, lambda *args: report())

print("Creating or updating local objects...", end='', flush=True)
for obj in objects(sys.stdin.buffer):
    try:
        obj = database.create_object(obj)
        spec = database.primary_spec(obj)
        if spec in current_objects:
            local_obj = session.fetch(*spec)
            if local_obj != obj:
                session.save(obj)
                stats["updated"] += 1
            else:
                stats["ignored"] += 1
            current_objects.remove(spec)
        else:
            session.save(obj)
            stats["created"] += 1
    except Exception as e:
        print("Error at object {!r}".format(obj))
        traceback.print_exc()
        stats["ignored"] += 1
print("Done")

print("Deleting local objects...", end='', flush=True)
for spec in current_objects:
    try:
        session.delete(session.fetch(*spec))
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
