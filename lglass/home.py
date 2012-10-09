# coding: utf-8

from lglass import application, bird, jinja2_env

@application.route("/")
def home():
	return jinja2_env.get_template("index.html").render()

