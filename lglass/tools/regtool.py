# coding: utf-8

import sys
import argparse
import json
import os
import os.path
import tempfile
import subprocess
import asyncore
import socket

import pkg_resources

import lglass.rpsl
import lglass.database
import lglass.database.cidr
import lglass.generators.roa
import lglass.whoisd

def _edit_object(editor, obj):
	with tempfile.NamedTemporaryFile("w+") as fh:
		fh.write(obj.pretty_print())
		fh.flush()
		subprocess.call([editor, fh.name])
		fh.seek(0)
		return lglass.rpsl.Object.from_iterable(fh)

def main_create_object(args, config, database):
	obj = lglass.rpsl.Object()
	obj.add(args.type, args.primary_key)
	kvpair_iter = iter(args.kvpairs)
	try:
		while True:
			key, value = next(kvpair_iter), next(kvpair_iter)
			obj.add(key, value)
	except StopIteration:
		pass
	
	if args.fill:
		try:
			schema = database.schema(args.type)
			for constraint in schema.constraints():
				if constraint.mandatory and constraint.key_name not in obj:
					obj.add(constraint.key_name, "# please insert {}".format(constraint.key_name))
		except KeyError:
			pass
	
	if args.edit:
		obj = _edit_object(args.editor, obj)

	database.save(obj)

def main_show_object(args, config, database):
	try:
		obj = database.get(args.type, args.primary_key)
	except KeyError:
		pass
	else:
		sys.stdout.write(obj.pretty_print(kv_padding=args.padding))

def main_validate_object(args, config, database):
	try:
		obj = database.get(args.type, args.primary_key)
		schema = database.schema(args.type)
	except KeyError:
		exit(111)
	else:
		try:
			schema.validate(obj)
		except lglass.rpsl.SchemaValidationError as e:
			print("{} {} is invalid: Key {}: {}".format(args.type, args.primary_key,
				e.key, e.message))
			exit(1)
		else:
			print("{} {} is valid".format(args.type, args.primary_key))
			exit(0)

def main_edit_object(args, config, database):
	try:
		obj = database.get(args.type, args.primary_key)
	except KeyError:
		exit(111)
	else:
		obj = _edit_object(args.editor, obj)
		database.save(obj)

def main_delete_object(args, config, database):
	database.delete(args.type, args.primary_key)

def main_list_objects(args, config, database):
	for spec in database.list():
		if args.types and spec[0] not in args.types:
			continue
		print(" ".join(spec))

def main_find_objects(args, config, database):
	database = lglass.database.cidr.CIDRDatabase(database)
	for obj in database.find(args.term):
		if args.types and obj.type not in args.types:
			continue
		print(obj.pretty_print())

def main_whoisd(args, config, database):
	if args.protocol == 4:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	elif args.protocol == 6:
		sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.bind((args.host, args.port))
	sock.listen(5)

	handler = lglass.whoisd.WhoisHandler(database)
	lglass.whoisd.WhoisdServer(sock, handler)
	asyncore.loop()

def main_roagen(args, config, database):
	if args.protocol == 4:
		routes = (database.get(*spec) for spec in database.list() if spec[0] == "route")
	elif args.protocol == 6:
		routes = (database.get(*spec) for spec in database.list() if spec[0] == "route6")
	if args.flush:
		print("flush roa table {table}".format(table=args.table))
	print("\n".join(lglass.generators.roa.roa_table(routes, args.table)))

def main_install_schemas(args, config, database):
	basedir = pkg_resources.resource_filename("lglass", "schemas")
	for schema in os.listdir(basedir):
		if schema[0] == ".":
			continue
		with open(os.path.join(basedir, schema)) as fh:
			obj = lglass.rpsl.Object.from_iterable(fh)
			database.save(obj)

def main(args=sys.argv[1:]):
	argparser = argparse.ArgumentParser(description="Registry management tool")

	argparser.add_argument("--config", "-c", help="Configuration file")
	argparser.add_argument("--editor", "-e", dest="editor", help="Editor (e.g. vim, nano)")

	subparsers = argparser.add_subparsers(dest="command", help="Command to execute")

	parser_help = subparsers.add_parser("help", help="Print help message")

	parser_create_object = subparsers.add_parser("create-object", help="Create object in registry")
	parser_create_object.add_argument("--fill", dest="fill", action="store_true", default=True, help="Prefill required fields with placeholders")
	parser_create_object.add_argument("--no-fill", dest="fill", action="store_false", help="Do not prefill required fields with placeholders")
	parser_create_object.add_argument("--edit", dest="edit", action="store_true", default=False, help="Start editor after creation")
	parser_create_object.add_argument("--no-edit", dest="edit", action="store_false", help="Do not start editor after creation")
	parser_create_object.add_argument("type")
	parser_create_object.add_argument("primary_key")
	parser_create_object.add_argument("kvpairs", nargs='*', help="List of key-value-pairs")

	parser_show_object = subparsers.add_parser("show-object", help="Show object in registry")
	parser_show_object.add_argument("--padding", "-p", default=8, type=int, help="Padding between key and value")
	parser_show_object.add_argument("type")
	parser_show_object.add_argument("primary_key")

	parser_validate_object = subparsers.add_parser("validate-object", help="Validate object in registry")
	parser_validate_object.add_argument("type")
	parser_validate_object.add_argument("primary_key")

	parser_edit_object = subparsers.add_parser("edit-object", help="Edit object in registry")
	parser_edit_object.add_argument("type")
	parser_edit_object.add_argument("primary_key")

	parser_delete_object = subparsers.add_parser("delete-object", help="Delete object in registry")
	parser_delete_object.add_argument("type")
	parser_delete_object.add_argument("primary_key")

	parser_list_objects = subparsers.add_parser("list-objects", help="List objects")
	parser_list_objects.add_argument("--type", "-T", dest="types", action="append")

	parser_find_objects = subparsers.add_parser("find-objects", help="Find objects")
	parser_find_objects.add_argument("--type", "-T", dest="types", action="append")
	parser_find_objects.add_argument("term")

	parser_whoisd = subparsers.add_parser("whoisd", help="Run whois server")
	parser_whoisd.add_argument("-4", dest="protocol", default=6, action="store_const", const=4, help="Listen on IPv4")
	parser_whoisd.add_argument("-6", dest="protocol", default=6, action="store_const", const=6, help="Listen on IPv6")
	parser_whoisd.add_argument("--host", "-H", dest="host", default="::", help="Listen on host")
	parser_whoisd.add_argument("--port", "-p", dest="port", default=4343, type=int, help="Listen on port")

	parser_roagen = subparsers.add_parser("roagen", help="Generate ROA tables")
	parser_roagen.add_argument("-4", dest="protocol", default=4, action="store_const", const=4)
	parser_roagen.add_argument("-6", dest="protocol", default=4, action="store_const", const=6)
	parser_roagen.add_argument("--flush", "-f", action="store_true", default=False)
	parser_roagen.add_argument("--table", "-t", default="roa1", type=str)

	parser_install_schemas = subparsers.add_parser("install-schemas", help="Install default schemas")

	args = argparser.parse_args(args)

	if args.editor is None:
		args.editor = os.environ.get("EDITOR", "vi")

	config = {
		"database": [
			"whois+lglass.database.file+file:./"
		]
	}
	if args.config is None:
		cwd = os.getcwd()
		cwd_path = None
		while not os.path.ismount(cwd):
			if os.path.exists(os.path.join(cwd, ".lglassrc")):
				cwd_path = os.path.join(cwd, ".lglassrc")
				break
			cwd = os.path.dirname(cwd)
		if cwd_path is not None:
			with open(cwd_path) as fh:
				config.update(json.load(fh))
	else:
		with open(args.config) as fh:
			config.update(json.load(fh))

	commands = {
		"create-object": main_create_object,
		"show-object": main_show_object,
		"validate-object": main_validate_object,
		"edit-object": main_edit_object,
		"delete-object": main_delete_object,
		"list-objects": main_list_objects,
		"find-objects": main_find_objects,
		"whoisd": main_whoisd,
		"roagen": main_roagen,
		"install-schemas": main_install_schemas
	}

	database = lglass.database.build_chain(config["database"])

	if args.command in commands:
		commands[args.command](args, config, database)
	else:
		argparser.print_help()

if __name__ == "__main__":
	main()

