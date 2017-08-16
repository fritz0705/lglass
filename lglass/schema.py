# coding: utf-8

import lglass.object

class SchemaObject(lglass.object.Object):
    def schema_keys(self):
        for constraint in self.get("key"):
            yield parse_constraint(constraint)

    def template(self):
        tpl = []
        for key_name, multiple, mandatory, inverse in self.schema_keys():
            t = ""
            t += "[mandatory] " if mandatory else "[optional]   "
            t += "[multiple] " if multiple  else "[single]    "
            t += "[inverse key]" if inverse else "[ ]"
            tpl.append((key_name, t))
        return tpl

def parse_constraint(constraint):
    key_name, *tokens = constraint.split()
    tokens_iter = iter(tokens)
    multiple = True
    mandatory = False
    inverse = []

    for token in tokens_iter:
        if token == "single":
            multiple = False
        elif token == "multiple":
            multiple = True
        elif token == "mandatory":
            mandatory = True
        elif token == "optional":
            mandatory = False
        elif token == "inverse":
            inverse = next(tokens_iter).split(",")
    
    return (key_name, multiple, mandatory, inverse)

def load_schema(db, typ):
    return SchemaObject(db.fetch("schema", typ.upper() + "-SCHEMA"))

