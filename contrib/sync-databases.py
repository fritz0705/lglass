#!/bin/python
# coding: utf-8

import argparse
import datetime

import lglass_sql.nic
import lglass.nic
import lglass.dn42

db_cls = lglass_sql.nic.NicDatabase

def sync(src, dst, dn42=False, delete=False, initial=False, filter_source=None):
    last_update = dst.manifest.last_modified_datetime

    for obj in src.find():
        if filter_source and obj.source != filter_source:
            continue
        if obj.last_modified_datetime > last_update or initial:
            if dn42:
                for fix in lglass.dn42.fix_object(obj):
                    yield ('ADD', fix.object_class, fix.primary_key)
                    dst.save(fix)
            else:
                yield ('ADD', obj.object_class, obj.primary_key)
                dst.save(obj)

    if delete:
        for obj in dst.find():
            original_primary_key = src.primary_key(obj)
            original_object = src.try_fetch(obj.object_class, original_primary_key)
            d = original_object is None or (obj.object_class in {"route", "route6"} and
                    obj["origin"] not in original_object.get("origin") and dn42)
            if d:
                yield ('DEL', obj.object_class, obj.primary_key)
                dst.delete(obj)

    dst.manifest.remove("last-modified")
    #dst.manifest.serial += 1
    dst.manifest.last_modified = datetime.datetime.now()
    dst.save_manifest()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
            description="Sync local database with DN42 database")
    argparser.add_argument("--src-type", default="nic")
    argparser.add_argument("--dst-type", default="nic")
    argparser.add_argument("--no-delete", action="store_true")
    argparser.add_argument("--initial", action="store_true")
    argparser.add_argument("--quiet", action="store_true")
    argparser.add_argument("--filter-source")
    argparser.add_argument("source")
    argparser.add_argument("destination")

    args = argparser.parse_args()
    from_dn42 = False

    if args.src_type == "nic":
        src = lglass.nic.FileDatabase(args.source)
    elif args.src_type == "dn42":
        from_dn42 = True
        src = lglass.dn42.DN42Database(args.source)
    elif args.src_type == "ipam":
        import lipam.ipam
        src = lipam.ipam.FileDatabase(args.source)

    if args.dst_type == "nic":
        db_cls = lglass_sql.nic.NicDatabase
    elif args.dst_type == "ipam":
        import lipam.sql
        db_cls = lipam.sql.IPAMDatabase

    dst = db_cls(args.destination)

    actions = []
    with dst.session() as sess:
        for action, object_class, object_key in sync(src, sess, dn42=from_dn42,
                delete=not args.no_delete,
                initial=args.initial,
                filter_source=args.filter_source):
            if not args.quiet:
                print("{} {}:   {}".format(action, object_class, object_key))
            actions.append((action, object_class, object_key))
        sess.commit()
