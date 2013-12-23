# coding: utf-8

import argparse
import json
import wsgiref.simple_server
import sys

import lglass.web.application

def main():
	argparser = argparse.ArgumentParser(description="Simple HTTP sevrer for lglass web interface")

	argparser.add_argument("--host", "-H", help="Bind to host", default="127.0.0.1")
	argparser.add_argument("--port", "-P", help="Bind to port", default="8080", type=int)
	argparser.add_argument("--config", "-c", help="Path to configuration file")

	args = argparser.parse_args()

	config = None
	if args.config is not None:
		with open(args.config) as fh:
			config = json.load(fh)
	
	app = lglass.web.application.MainApp(config)

	httpd = wsgiref.simple_server.make_server(args.host, args.port, app)
	print("Serving HTTP on {host}:{port}...".format(host=args.host, port=args.port))

	httpd.serve_forever()
	
if __name__ == '__main__':
	main()

