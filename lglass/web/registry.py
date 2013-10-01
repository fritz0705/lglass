# coding: utf-8

def show_object(app, type, primary_key):
	try:
		obj = app.registry.get(type, primary_key)
	except KeyError:
		app.abort(404, "Object not found")

	try:
		schema = app.registry.schema(obj.type)
	except KeyError:
		pass
	
	inverses = set()

	items = []
	for key, value in obj:
		inverse = list(schema.find_inverse(app.registry, key, value))
		inverses.update(inverse)
		items.append((key, value, inverse))
	
	inverses = sorted(inverses, key=lambda o: o.spec)

	return app.render("registry/show_object.html",
		inverses=inverses,
		object=obj,
		items=items
	)

def show_objects(app, type):
	specs = [spec for spec in sorted(app.registry.list()) if spec[0] == type]
	return app.render("registry/show_objects.html",
		specs=specs,
		type=type
	)

def show_object_types(app):
	types = sorted(app.registry.object_types)
	return app.render("registry/show_object_types.html",
		types=types
	)

