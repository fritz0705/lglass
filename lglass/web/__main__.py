# coding: utf-8

import argparse
import json
import wsgiref.simple_server
import sys

import lglass.web.application

def load_config(filename):
	with open(filename) as fh:
		return json.load(fh)
	return None

def main():
	argparser = argparse.ArgumentParser(description="Simple HTTP sevrer for lglass web interface")

	argparser.add_argument("--host", "-H", help="Bind to host", default="127.0.0.1")
	argparser.add_argument("--port", "-P", help="Bind to port", default="8080", type=int)
	argparser.add_argument("--config", "-c", help="Path to configuration file")

	args = argparser.parse_args()

	app = lglass.web.application.app

	if args.config is not None:
		try:
			config = load_config(args.config)
		except FileNotFoundError:
			sys.stderr.write("Fatal: Could not find file {}\n".format(args.config))
			exit(111)

		def _config_middleware(environ, start_response):
			environ["lglass-web.config"] = config
			return lglass.web.application.app(environ, start_response)
		app = _config_middleware

	httpd = wsgiref.simple_server.make_server(args.host, args.port, app)
	print("Serving HTTP on {host}:{port}...".format(host=args.host, port=args.port))

	httpd.serve_forever()
	
if __name__ == '__main__':
	main()

