# coding: utf-8

def absolute(domain, zone=""):
	if domain[-1] == '.':
		return domain
	if zone and zone[-1] != '.':
		zone = zone + '.'
	return domain + '.' + zone

def email(mail):
	if "@" not in mail:
		return absolute(mail)
	local, remote = mail.split("@", 1)
	return local.replace(".", "\\.") + "." + absolute(remote)

class ResourceRecord(object):
	name = None
	ttl = None
	klass = None
	type = None
	data = None

	def __init__(self, *args):
		self.data = []
		self.klass = "IN"

		args_iter = iter(args)
		try:
			self.name = next(args_iter)
			token = next(args_iter)
			if isinstance(token, int):
				self.ttl = token
				token = next(args_iter)
			if token in ["CH", "IN", "HS", "CS"]:
				self.klass = token
				token = next(args_iter)
			self.type = token
			self.data = list(map(str, args_iter))
		except StopIteration:
			raise ValueError("Too few arguments for ResourceRecord")

		self.name = absolute(self.name)
	
	def set_default_ttl(self, ttl):
		if self.ttl is None:
			self.ttl = ttl

	def __str__(self):
		builder = [self.name]
		if self.ttl:
			builder.append(self.ttl)
		builder.extend([self.klass, self.type])
		builder.extend(self.data)
		return " ".join(builder)

	def __repr__(self):
		builder = [self.name]
		if self.ttl:
			builder.append(self.ttl)
		builder.extend([self.klass, self.type])
		builder.extend(self.data)
		return "{0}({1})".format(self.__class__.__name__,
			", ".join(repr(b) for b in builder))
	
	def __hash__(self):
		return hash(self.name) ^ hash(self.ttl) ^ hash(self.klass) ^ hash(self.type) ^ hash(tuple(self.data))

