#!/bin/python

import argparse
import datetime

import lglass.nic
import lglass.dn42

def sync(src, dst, dn42=False, delete=True):
    last_update = dst.manifest.last_modified_datetime

    for obj in src.find():
        if obj.last_modified_datetime > last_update:
            if src.database_name not in obj:
                obj.append("source", src.database_name)
            if dn42:
                for fix in lglass.dn42.fix_object(obj):
                    yield ('ADD', fix.object_class, fix.primary_key)
                    dst.save(fix)
            else:
                yield ('ADD', obj.object_class, obj.primary_key)
                dst.save(obj)

    if delete:
        for obj in dst.find():
            if src.database_name not in obj.get("source"):
                continue
            original_primary_key = src.primary_key(obj)
            original_object = src.try_fetch(obj.object_class, original_primary_key)
            d = original_object is None or (obj.object_class in {"route", "route6"} and
                    obj["origin"] not in original_object.get("origin") and dn42)
            if d:
                yield ('DEL', obj.object_class, obj.primary_key)
                dst.delete(obj)

    dst.manifest.remove("last-modified")
    dst.manifest.last_modified = datetime.datetime.now()
    dst.save_manifest()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
            description="Sync local database with DN42 database")
    argparser.add_argument("--from-dn42", action="store_true")
    argparser.add_argument("--no-delete", action="store_true")
    argparser.add_argument("--mqtt-broker")
    argparser.add_argument("--mqtt-topic")
    argparser.add_argument("--quiet", action="store_true")
    argparser.add_argument("source")
    argparser.add_argument("destination")

    args = argparser.parse_args()

    if args.from_dn42:
        src = lglass.dn42.DN42Database(args.source)
    else:
        src = lglass.nic.FileDatabase(args.source)
    dst = lglass.nic.FileDatabase(args.destination)

    actions = []
    for action, object_class, object_key in sync(src, dst, dn42=args.from_dn42,
            delete=not args.no_delete):
        if not args.quiet:
            print("{} {}:   {}".format(action, object_class, object_key))
        actions.append((action, object_class, object_key))

    if args.mqtt_broker:
        import paho.mqtt.client as mqtt
        mqttc = mqtt.Client()
        mqttc.connect(args.mqtt_broker)
        mqttc.loop_start()
        for a in actions:
            mqttc.publish(args.mqtt_topic, "{} {}: {}".format(*a))
        mqttc.loop_stop(force=False)

