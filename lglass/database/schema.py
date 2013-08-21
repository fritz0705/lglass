# coding: utf-8

import urllib.parse

import lglass.rpsl
import lglass.database.base

@lglass.database.base.register("schema")
class SchemaDatabase(lglass.database.base.Database):
	""" The inverse databases resolves inverse relationships on find() and also
	validates the schema of objects. """

	schema_validation_field = "x-schema-valid"
	hidden_attr_field = "x-hidden"

	hide_attributes = True
	resolve_inverse = True

	inverse_type_filter = staticmethod(lambda key: True)

	def __init__(self, db, **kwargs):
		self.database = db
		self.__dict__.update(kwargs)

	def get(self, type, primary_key):
		obj = self.database.get(type, primary_key)
		if self.schema_validation_field:
			self._validate_schema(obj)
		if self.hide_attributes:
			self._hide_attributes(obj)
		return obj

	def find(self, primary_key, types=None):
		objs = self.database.find(primary_key, types)

		if self.resolve_inverse:
			objs.extend(self.find_inverse_objects(objs))

		if self.schema_validation_field is not None:
			for obj in objs:
				self._validate_schema(obj)
		if self.hide_attributes:
			for obj in objs:
				self._hide_attributes(obj)

		return objs

	def save(self, object):
		self.database.save(object)

	def delete(self, type, primary_key):
		self.database.delete(type, primary_key)

	def list(self):
		return self.database.list()

	def __hash__(self):
		return hash(self.database)

	def find_inverse_objects(self, objs):
		if isinstance(objs, lglass.rpsl.Object):
			objs = [objs]
		seen = set(obj.spec for obj in objs)
		inverse_objs = []
		for obj in objs:
			try:
				schema = self.schema(obj.type)
			except KeyError:
				continue
			for constraint in schema.constraints():
				if constraint.inverse is None:
					continue

				for inverse in constraint.inverse:
					for key, value in obj.get(constraint.key_name):
						if not self.inverse_type_filter(inverse):
							continue
						if (inverse, value) not in seen:
							try:
								inv_obj = self.get(inverse, value)
							except KeyError:
								pass
							else:
								seen.add((inverse, value))
								inverse_objs.append(inv_obj)
		return inverse_objs
	
	def _validate_schema(self, obj):
		if self.schema_validation_field in obj:
			return
		try:
			schema = self.schema(obj.type)
			schema.validate(obj)
		except lglass.rpsl.SchemaValidationError as e:
			obj.add(self.schema_validation_field, "INVALID {} {}".format(e.args[0], e.args[1]))
		except KeyError:
			obj.add(self.schema_validation_field, "UNKNOWN")
		else:
			obj.add(self.schema_validation_field, "VALID")
	
	def _hide_attributes(self, obj):
		try:
			schema = self.schema(obj.type)
		except KeyError:
			return

		hidden = set()

		for constraint in schema.constraints():
			if constraint.hidden:
				hidden.add(constraint.key_name)
				del obj[constraint.key_name]

		if self.hidden_attr_field and hidden:
			obj[self.hidden_attr_field] = " ".join(sorted(hidden))
	
	@classmethod
	def from_url(cls, url):
		self = cls(None)

		if url.query:
			query = urllib.parse.parse_qs(url.query)
			if "types-include" in query:
				types = query["types-include"][-1].split(",")
				self.inverse_type_filter = lambda t: t in types
			if "types-exclude" in query:
				types = query["types-exclude"][-1].split(",")
				self.inverse_type_filter = lambda t: t not in types
			if "schema-validation-field" in query:
				self.schema_validation_field = query["schema-validation-field"][-1]
			if "hidden-attr-field" in query:
				self.hidden_attr_field = query["hidden-attr-field"][-1]
			if "hide-attributes" in query:
				self.hide_attributes = True if query["hide-attributes"][-1] == "true" else False
			if "resolve-inverse" in query:
				self.resolve_inverse = True if query["resolve-inverse"][-1] == "true" else False

		return self

InverseDatabase = SchemaDatabase
