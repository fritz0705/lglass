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
    def ipv6_prefixes(self):
        return list(map(netaddr.IPNetwork, self.get("ipv6-prefix")))

    def ipv6_slaacs(self):
        slaacs = []
        for l2_address in self.l2_addresses:
            for prefix in self.ipv6_prefixes:
                slaacs.append(l2_address.ipv6(prefix.value))
        return slaacs

    @property
    def l2_addresses(self):
        return list(map(netaddr.EUI, self.get("l2-address")))

    @property
    def primary_l2_address(self):
        return netaddr.EUI(self["l2-address"])

    @property
    def status(self):
        return self.getfirst("status")

    @status.setter
    def status(self, new_status):
        self["status"] = new_status

    @status.deleter
    def status(self):
        del self["status"]

    @property
    def inverse_keys(self):
        return super().inverse_keys + ["l2-address", "ipv6-prefix", "address"]

    def inverse_fields(self):
        yield from super().inverse_fields()
        for l2addr in self.get("l2-address"):
            yield ("l2-address", l2addr.lower())
        for ipv6prefix in self.get("ipv6-prefix"):
            yield ("ipv6-prefix", ipv6prefix.lower())
        for address in self.get("address"):
            yield ("address", address.lower())


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
    def hostnames(self):
        return list(self.get("hostname"))

    @property
    def primary_host(self):
        return self["host"]

    @primary_host.setter
    def primary_host(self, new_host):
        self["host"] = new_host

    @property
    def status(self):
        try:
            return self["status"]
        except BaseException:
            pass

    @property
    def inverse_keys(self):
        return super().inverse_keys + ["host", "l2-address"]

    def inverse_fields(self):
        yield from super().inverse_fields()
        for host in self.get("host"):
            yield ("host", host)
        for l2addr in self.get("l2-address"):
            yield ("l2-address", l2addr.lower())


class SegmentObject(lglass.nic.NicObject):
    @property
    def networks(self):
        return list(self.get("net"))

    @property
    def vlan_id(self):
        return int(self["vlan-id"])

    @property
    def vxlan_vni(self):
        return int(self["vxlan-vni"])

    @property
    def members(self):
        pass

    @property
    def inverse_keys(self):
        return super().inverse_keys + ["net", "vlan-id", "vxlan-vni"]

    def inverse_fields(self):
        yield from super().inverse_fields()
        for net in self.get("net"):
            yield ("net", net.lower())
        for vlanid in self.get("vlan-id"):
            yield ("vlan-id", vlanid)
        for vxlanvni in self.get("vxlan-vni"):
            yield ("vxlan-vni", vxlanvni)


class IPAMDatabaseMixin(lglass.nic.NicDatabaseMixin):
    def __init__(self):
        lglass.nic.NicDatabaseMixin.__init__(self)
        self.object_class_types = dict(self.object_class_types)
        self.object_class_types.update({
            "address": AddressObject,
            "host": HostObject,
            "segment": SegmentObject})
        self.object_classes = set(self.object_classes)
        self.object_classes.update({"address", "host", "segment"})


class FileDatabase(lglass.nic.FileDatabase, IPAMDatabaseMixin):
    def __init__(self, *args, **kwargs):
        lglass.nic.FileDatabase.__init__(self, *args, **kwargs)
        IPAMDatabaseMixin.__init__(self)


if __name__ == "__main__":
    import lglass.lipam
    lglass.lipam.main()
