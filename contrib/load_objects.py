#!/bin/python

import sys

import lglass.nic
import lglass.object

db = lglass.nic.FileDatabase(sys.argv[1])


def objects(lines):
    obj = []
    for line in lines:
        if not line.strip() and obj:
            yield obj
            obj = []
        elif line[0] in {'%', '#'} or not line.strip():
            continue
        else:
            obj.append(line)
    if obj:
        yield obj


for obj in objects(sys.stdin.readlines()):
    obj = lglass.object.parse_object(obj)
    obj = db.object_class_type(obj[0][0])(obj)

    original_object = db.try_fetch(obj.object_class, db.primary_key(obj))
    if original_object and (original_object.source != obj.source):
        print("Skip {} {}".format(obj.object_class, db.primary_key(obj)))
        continue

    db.save(obj)
    print("Save {} {}".format(obj.object_class, db.primary_key(obj)))
