#!/bin/python
# coding: utf-8

import lglass.nic

database = lglass.nic.FileDatabase()

if hasattr(database, "session"):
    session = database.session()
else:
    session = database

print("# Database export from database {}".format(database.database_name))
print("# Current time: {}".format(datetime.datetime.now()))
print()

for spec in session.lookup():
    print(session.fetch(spec))

if hasattr(session, "close"):
    session.close()

