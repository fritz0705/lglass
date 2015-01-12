# coding: utf-8

import os
import os.path

import lglass.rpsl
import lglass.registry
import lglass.database.base

@lglass.database.base.register("file")
class FileDatabase(lglass.registry.FileRegistry):
	@classmethod
	def from_url(cls, url):
		return cls(url.path)

