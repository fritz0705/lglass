# coding: utf-8

import os
import os.path

class RPSLObject:
	def __init__(self, data=None):
		self.data = list()
		if data:
			self.extend(data)
	
	def extend(self, data):
		if isinstance(data, list) or isinstance(data, RPSLObject):
			return self.data.extend(data)
	
	def __getitem__(self, key):
		return self.data[key]

	def __setitem__(self, key, value):
		self.data[key] = value

	def __contains__(self, key):
		return key in self.data

	def __len__(self):
		return len(self.data)

	def __iter__(self):
		return iter(self.data)

	def __repr__(self):
		return repr(self.data)

	def __str__(self):
		result = []
		for key, value in self.data:
			result.append("{0}: {1}".format(key, value))
		return "\n".join(result)

	@property
	def type(self):
		return self[0][0]

def parse_rpsl(lines):
	last = None
	for line in lines:
		if not line.strip():
			continue
		if line[0] == '%':
			continue
		if line[0] == ' ' and last:
			last[1] = last[1] + " " + line.strip()
			continue

		if last:
			yield last[0], last[1]
		key, value = map(lambda p: p.strip(), line.split(":", 1))
		last = [key, value]
	if last:
		yield last[0], last[1]

