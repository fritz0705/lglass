# coding: utf-8

import netaddr

import lglass.nic

class HostObject(lglass.nic.NicObject):
    @property
    def addresses(self):
        return list(self.get("address"))

    @property
    def primary_address(self):
        return netaddr.IPAddress(self["address"])

    @property
    def l2_addresses(self):
        return list(self.get("l2-address"))

    @property
    def primary_l2_address(self):
        return self["l2-address"]

    @property
    def status(self):
        return self.getfirst("status")

    @status.setter
    def status(self, new_status):
        self["status"] = new_status

    @status.deleter
    def status(self):
        del self["status"]

class AddressObject(lglass.nic.NicObject):
    @property
    def ip_address(self):
        return netaddr.IPAddress(self.object_key)

    @ip_address.setter
    def ip_address(self, new_ip):
        if isinstance(new_ip, str):
            new_ip = netaddr.IPAddress(new_ip)
        elif isinstance(new_ip, netaddr.IPNetwork):
            new_ip = new_ip.ip
        self.object_key = str(new_ip)

    @property
    def ip_network(self):
        return netaddr.IPNetwork(self.object_key)

    @property
    def name(self):
        return self.getfirst("name")

    @name.setter
    def name(self, new_name):
        self["name"] = new_name

    @name.deleter
    def name(self):
        del self["name"]

    @property
    def ip_version(self):
        return self.ip_address.version

    @property
    def l2_addresses(self):
        return list(self.get("l2-address"))

    @property
    def primary_l2_address(self):
        return self["l2-address"]

    @property
    def hosts(self):
        return list(self.get("host"))

    @hosts.setter
    def hosts(self, new_hosts):
        del self["host"]
        self["host"] = new_hosts

    @property
    def primary_host(self):
        return self["host"]

    @primary_host.setter
    def primary_host(self, new_host):
        self["host"] = new_host

class IPAMDatabaseMixin(lglass.nic.NicDatabaseMixin):
    def __init__(self):
        lglass.nic.NicDatabaseMixin.__init__(self)
        self.object_class_types = dict(self.object_class_types)
        self.object_class_types.update({
            "address": AddressObject,
            "host": HostObject})
        self.object_classes = set(self.object_classes)
        self.object_classes.update({"address", "host"})

class FileDatabase(lglass.nic.FileDatabase, IPAMDatabaseMixin):
    def __init__(self, *args, **kwargs):
        lglass.nic.FileDatabase.__init__(self, *args, **kwargs)
        IPAMDatabaseMixin.__init__(self)

