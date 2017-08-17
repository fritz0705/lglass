# coding: utf-8

import socket

import lglass.object


class WhoisClient(object):
    def __init__(self, address, port=43, flavour='RIPE', database=None):
        self.address = address
        self.port = port
        self.flavour = flavour
        self.database = None

    def create_object(self, data, object_class=None):
        if self.database is not None:
            return self.database.create_object(data, object_class=object_class)
        return lglass.object.Object(data)

    def build_query(self, term, classes=None, reverse_domain=False,
                    recursive=True, exact=False, inverse_attributes=None):
        query = []
        if classes is not None:
            query.append("-T")
            if isinstance(classes, str):
                query.append(classes)
            elif isinstance(classes, (list, set)):
                query.append(",".join(classes))
        if reverse_domain:
            query.append("-d")
        if not recursive:
            query.append("-r")
        if exact:
            query.append("-x")
        if inverse_attributes is not None:
            query.append("-i")
            if isinstance(inverse_attributes, str):
                query.append(inverse_attributes)
            elif isinstance(inverse_attributes, (list, set)):
                query.append(",".join(inverse_attributes))
        if isinstance(term, str):
            query.append(term)
        elif isinstance(term, (list, str)):
            for t in term:
                query.append(t)
        return query

    def query(self, *args, **kwargs):
        query = " ".join(self.build_query(*args, **kwargs)).encode() + b"\n"
        response = b""
        with socket.create_connection((self.address, self.port)) as conn:
            conn.sendall(query)
            while True:
                buf = conn.recv(1024)
                if not buf:
                    break
                response += buf
        response = response.decode().splitlines()
        for obj in lglass.object.parse_objects(response):
            yield self.create_object(obj)
