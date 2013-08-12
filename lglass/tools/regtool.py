# coding: utf-8

import sys
import argparse
import json
import pkg_resources
import os
import os.path

import lglass.database
import lglass.rpsl

def main_create_db(args, config, database):
	if args.with_schemas:
		directory = pkg_resources.resource_filename("lglass", "schemas")
		for schema in os.listdir(directory):
			if schema[0] == '.': continue
			with open(os.path.join(directory, schema)) as fh:
				obj = lglass.rpsl.Object.from_iterable(fh)
				database.save(obj)

def main_delete_object(args, config, database):
	database.delete(args.type, args.primary_key)

def main_create_object(args, config, database):
	obj = lglass.rpsl.Object()
	if args.stdin:
		input_obj = lglass.rpsl.Object.from_iterable(sys.stdin)
		obj.extend(input_obj)
	if args.fill:
		schema = database.schema(args.type)
		for constraint in schema.constraints:
			if constraint.mandatory and constraint.key_name not in obj:
				obj.add(constraint.key_name, "# Insert value for {} here".format(constraint.key_name))
	obj[0] = (args.type, args.primary_key)

	database.save(obj)

def main_validate_object(args, config, database):
	schema = database.schema(args.type)
	obj = database.get(args.type, args.primary_key)

	validation_result = schema.validate(obj)
	try:
		schema.validate(obj)
		print("Validation passed")
		exit(0)
	except lglass.rpsl.SchemaValidationError as exc:
		print("Validation failed: Key {}: {}".format(exc.key, exc.message))
		exit(1)
	finally:
		exit(111)

def main_show_object(args, config, database):
	obj = database.get(args.type, args.primary_key)
	sys.stdout.write(obj.pretty_print(kv_padding=args.padding))

def main(args=sys.argv[1:]):
	argparser = argparse.ArgumentParser(description="Registry management tool")

	argparser.add_argument("--config", "-c", help="Configuration file")
	argparser.add_argument("--database", "-D", help="Path to database")

	subparsers = argparser.add_subparsers(dest="command")

	parser_create_object = subparsers.add_parser("create-object")
	parser_create_object.add_argument("--fill", dest="fill", action="store_true", default=True)
	parser_create_object.add_argument("--no-fill", dest="fill", action="store_false")
	parser_create_object.add_argument("-S", "--stdin", default=False, action="store_true")
	parser_create_object.add_argument("type")
	parser_create_object.add_argument("primary_key")

	parser_show_object = subparsers.add_parser("show-object")
	parser_show_object.add_argument("--padding", "-p", default=8, type=int)
	parser_show_object.add_argument("type")
	parser_show_object.add_argument("primary_key")

	parser_validate_object = subparsers.add_parser("validate-object")
	parser_validate_object.add_argument("type")
	parser_validate_object.add_argument("primary_key")

	parser_create_db = subparsers.add_parser("create-db")
	parser_create_db.add_argument("--with-schemas", dest="with_schemas", action="store_true", default=True)
	parser_create_db.add_argument("--without-schemas", dest="with_schemas", action="store_false")

	parser_delete_object = subparsers.add_parser("delete-object")
	parser_delete_object.add_argument("type")
	parser_delete_object.add_argument("primary_key")

	args = argparser.parse_args(args)

	config = {
		"database.path": ".",
		"database.type": "file"
	}
	if args.config is not None:
		with open(args.config) as fh:
			config.update(json.load(fh))
	
	for key, value in {
		"database.path": args.database
	}.items():
		if value is not None:
			config[key] = value
	
	database = {
		"file": lglass.database.FileDatabase,
		"sqlite3": lglass.database.SQLite3Database
	}[config["database.type"]](config["database.path"])

	{
		"create-object": main_create_object,
		"create-db": main_create_db,
		"delete-object": main_delete_object,
		"show-object": main_show_object,
		"validate-object": main_validate_object,
		None: (lambda args, config, database: argparser.print_help())
	}[args.command](args=args, config=config, database=database)

if __name__ == "__main__":
	main()

