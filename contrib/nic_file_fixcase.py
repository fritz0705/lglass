#!/bin/python
# coding: utf-8

import sys

import lglass.nic
import lglass.object

old_db = lglass.nic.FileDatabase(sys.argv[1], case_insensitive=False)
new_db = lglass.nic.FileDatabase(sys.argv[1], case_insensitive=True)

for obj in old_db.find():
    old_db.delete(obj)
    new_db.save(obj)

