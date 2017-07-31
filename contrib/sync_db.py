#!/bin/python

import argparse
import datetime

import lglass.nic
import lglass.dn42

argparser = argparse.ArgumentParser(
        description="Sync local database with DN42 database")
argparser.add_argument("src")
argparser.add_argument("dst")

args = argparser.parse_args()

src = lglass.dn42.DN42Database(args.src)
dst = lglass.nic.FileDatabase(args.dst)

last_update = dst.manifest.last_modified_datetime

for obj in src.find():
    if obj.last_modified_datetime > last_update:
        if src.database_name not in obj:
            obj.append("source", src.database_name)
        print("Update {} {}".format(obj.object_class, obj.primary_key))
        for fix in lglass.dn42.fix_object(obj):
            dst.save(fix)

for obj in dst.find():
    if src.database_name not in obj.get("source"):
        continue
    original_primary_key = src.primary_key(obj)
    original_object = src.try_fetch(obj.object_class, original_primary_key)
    delete = original_object is None or (obj.object_class in {"route", "route6"} and
            obj["origin"] not in original_object.get("origin"))
    if delete:
        print(original_primary_key)
        print("Delete {} {}".format(obj.object_class, obj.primary_key))
        dst.delete(obj)

dst.manifest.remove("last-modified")
dst.manifest.last_modified = datetime.datetime.now()
dst.save_manifest()

