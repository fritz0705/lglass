import datetime
import os
import re

import dateutil.parser
import netaddr

import lglass.database
import lglass.dns
import lglass.object


def parse_asn(asn):
    """Parse a string containing an autonomous system number, returning the
    autonomous system number as int."""
    try:
        return int(asn)
    except ValueError:
        pass
    m = re.match("[aA][sS]([0-9]+)$", asn)
    if m:
        return int(m[1])


def parse_as_block(as_block):
    """Parse a string describing a block of autonomous system numbers,
    returning a tuple of the first and last numbers."""
    m = re.match(
        r"([Aa][Ss])?([0-9]+)\s*[-_/]\s*([Aa][Ss])?([0-9]+)$", as_block)
    if not m:
        return False
    return int(m[2]), int(m[4])


def parse_ip_range(string):
    start, end = map(lambda s: s.strip(), string.split("-", 1))
    return netaddr.IPRange(start, end)


class NicObject(lglass.object.Object):
    """Object from a NicDatabase"""

    @property
    def source(self):
        """Source database of the object."""
        try:
            return self["source"].split("#")[0].strip()
        except KeyError:
            pass

    @source.setter
    def source(self, new_source):
        self["source"] = new_source

    @source.deleter
    def source(self):
        del self["source"]

    @property
    def source_flags(self):
        """Source flags of the object."""
        try:
            return self["source"].split("#")[1].split()
        except (KeyError, IndexError):
            return []

    @source_flags.setter
    def source_flags(self, new_flags):
        if new_flags:
            if isinstance(new_flags, str):
                new_flags = [new_flags]
            self["source"] = self.source + " # " + " ".join(new_flags)
        else:
            self["source"] = self.source

    @source_flags.deleter
    def source_flags(self):
        self["source"] = self.source

    @property
    def maintainers(self):
        """List of maintainer objects."""
        ret = []
        for maintainers in self.get("mnt-by"):
            ret.extend(map(str.strip, maintainers.split(",")))
        return ret

    @maintainers.setter
    def maintainers(self, new_maintainers):
        try:
            mnt_index = self.indices("mnt-by")[0]
        except BaseException:
            pass

    @maintainers.deleter
    def maintainers(self):
        del self["mnt-by"]

    @property
    def created(self):
        """Date and time of creation."""
        try:
            return self["created"]
        except KeyError:
            pass

    @created.setter
    def created(self, new_date):
        if isinstance(new_date, (int, float)):
            new_date = datetime.datetime.fromtimestamp(
                new_date, tz=datetime.timezone.utc)
        elif isinstance(new_date, str):
            new_date = dateutil.parser.parse(new_date)
        self["created"] = new_date.astimezone(
            tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def last_modified(self):
        """Date and time of last modification."""
        try:
            return self["last-modified"]
        except KeyError:
            pass

    @last_modified.setter
    def last_modified(self, new_date):
        if isinstance(new_date, (int, float)):
            new_date = datetime.datetime.fromtimestamp(
                new_date, tz=datetime.timezone.utc)
        elif isinstance(new_date, str):
            new_date = dateutil.parser.parse(new_date)
        self["last-modified"] = new_date.astimezone(
            tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def last_modified_datetime(self):
        if self.last_modified is not None:
            return dateutil.parser.parse(self.last_modified)
        else:
            return datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)

    @property
    def description(self):
        """Description of the object."""
        return self["descr"]

    @description.setter
    def description(self, new_descr):
        self["descr"] = new_descr

    @description.deleter
    def description(self):
        del self["descr"]

    @property
    def inverse_keys(self):
        """List of inverse keys."""
        return ["abuse-c", "abuse-mailbox", "admin-c", "auth", "author",
                "ds-rdata", "fingerpr", "form", "ifaddr", "irt-nfy",
                "local-as", "mbrs-by-ref", "member-of", "mnt-by",
                "mnt-domains", "mnt-irt", "mnt-lower", "mnt-nfy", "mnt-ref",
                "mnt-routes", "notify", "nserver", "org", "origin", "ping-hdl",
                "ref-nfy", "tech-c", "upd-to", "zone-c"]

    def inverse_fields(self):
        """Generator that yields key-value-tuples, representing key and
        index values of an inverse field."""
        # Simple object references
        for class_ in {"abuse-c", "admin-c", "author", "form", "local-as",
                       "mnt-domains", "mnt-irt",
                       "mnt-lower", "mnt-ref", "org", "origin", "ping-hdl",
                       "tech-c", "zone-c"}:
            for value in self.get(class_):
                yield (class_, value)
        # Object list references
        for class_ in {"member-of", "members", "mbrs-by-ref", "mnt-by"}:
            for values in self.get(class_):
                for value in values.split(","):
                    if class_ == "mbrs-by-ref" and value.strip() == "ANY":
                        continue
                    yield (class_, value.strip())
        # Email addresses
        for class_ in {"abuse-mailbox", "irt-nfy", "mnt-nfy", "notify",
                "ref-nfy", "upd-to"}:
            for value in self.get(class_):
                yield (class_, value)
        # Special handling for auth
        for auth in self.get("auth"):
            if auth.startswith("PGPKEY-") or auth.startswith("X509-"):
                yield ("auth", auth)
        # Free-form information
        for class_ in {"ds-rdata", "fingerpr"}:
            for value in self.get(class_):
                yield (class_, value[:128])
        # Special handling for mnt-routes
        for mntroutes in self.get("mnt-routes"):
            mntroutes = mntroutes.split()[0]
            yield ("mnt-routes", mntroutes)
        # Special handling for ifaddr
        for ifaddr in self.get("ifaddr"):
            ifaddr = ifaddr.lower().split()[0]
            yield ("ifaddr", ifaddr)
        # Special handling for nserver
        for nserver in self.get("nserver"):
            for n in nserver.lower().split():
                yield ("nserver", n)


class HandleObject(NicObject):
    """Object describing a NIC handle."""

    @property
    def primary_key_fields(self):
        return ["nic-hdl"]


class InetnumObject(NicObject):
    """Object describing an Internet number resource."""

    def add(self, key, value, index=None):
        try:
            return super().add(key, value, index)
        finally:
            if key == self.object_class:
                self.ip_network = self.ip_network

    @property
    def ip_range(self):
        """IP address range described by the object."""
        if "-" in self.object_key:
            return parse_ip_range(self.object_key)
        net = self.ip_network
        return netaddr.IPRange(net[0], net[-1])

    @property
    def ip_network(self):
        """IP network described by the object."""
        try:
            return netaddr.IPNetwork(self.object_key)
        except netaddr.core.AddrFormatError:
            pass
        return self.ip_range.cidrs()[0]

    @ip_network.setter
    def ip_network(self, new_ip_network):
        if isinstance(new_ip_network, str):
            if "-" in new_ip_network:
                new_ip_network = parse_ip_range(new_ip_network)
            else:
                new_ip_network = netaddr.IPNetwork(new_ip_network)
        if "-" in self.object_key and isinstance(
                new_ip_network, netaddr.IPNetwork):
            new_ip_network = netaddr.IPRange(
                new_ip_network[0], new_ip_network[-1])
        if isinstance(new_ip_network, netaddr.IPNetwork):
            self.object_key = str(new_ip_network)
        elif isinstance(new_ip_network, netaddr.IPRange):
            self.object_key = "{} - {}".format(new_ip_network[0],
                                               new_ip_network[-1])
        if new_ip_network.version == 4:
            self.object_class = "inetnum"
        elif new_ip_network.version == 6:
            self.object_class = "inet6num"

    @property
    def ip_networks(self):
        """IP networks for legacy range objects, if multiple CIDR networks
        apply. Read-only attribute."""
        try:
            return [netaddr.IPNetwork(self.object_key)]
        except netaddr.core.AddrFormatError:
            pass
        return self.ip_range.cidrs()

    @property
    def is_legacy(self):
        """Return True when this object is legacy, i.e. it stands for multiple
        CIDR networks."""
        return len(self.ip_networks) > 1

    @property
    def ip_version(self):
        """IP version."""
        if self.object_class == "inet6num":
            return 6
        elif self.object_class == "inetnum":
            return 4

    def rdns_domains(self):
        """List of rDNS domains."""
        net = self.ip_network
        if self.ip_version == 4:
            next_prefixlen = 8 * ((net.prefixlen - 1) // 8 + 1)
        elif self.ip_version == 6:
            next_prefixlen = 4 * ((net.prefixlen - 1) // 4 + 1)
        for subnet in net.subnet(next_prefixlen):
            yield (subnet, lglass.dns.rdns_domain(subnet))

    @property
    def primary_key(self):
        if self.is_legacy:
            r = self.ip_range
            return str("{} - {}".format(r[0], r[-1]))
        return str(self.ip_network)

    @property
    def route_maintainers(self):
        """List of maintainers for matching route objects."""
        return list(self.get("mnt-routes"))

    @property
    def irt_maintainers(self):
        """List of Incident Response Teams."""
        return list(self.get("mnt-irt"))

    @property
    def domain_maintainers(self):
        """List of maintainers for matching rDNS domain objects."""
        return list(self.get("mnt-domains"))

    @property
    def lower_maintainers(self):
        """List of maintainers for suballocations."""
        return list(self.get("mnt-lower"))


class ASBlockObject(NicObject):
    """Object describing an as-block in a NIC database."""

    def __contains__(self, number_or_key):
        if isinstance(number_or_key, int):
            return number_or_key in self.range
        return NicObject.__contains__(self, number_or_key)

    @property
    def start(self):
        """First autonomous system number in the block."""
        return self.range.start

    @property
    def end(self):
        """Last autonomous system number in the block."""
        return self.range.stop - 1

    @property
    def range(self):
        """range object, starting with the first and ending with the last
        autonomous system number in the block."""
        start, end = parse_as_block(self.object_key)
        return range(start, end + 1)

    @property
    def primary_key(self):
        return "AS{} - AS{}".format(self.start, self.end)


class RouteObject(NicObject):
    """Object describing a route in a NIC database."""
    @property
    def ip_network(self):
        if self.ip_version == 6:
            return netaddr.IPNetwork(self["route6"])
        elif self.ip_version == 4:
            return netaddr.IPNetwork(self["route"])

    @property
    def ip_version(self):
        if self.object_class == "route6":
            return 6
        elif self.object_class == "route":
            return 4

    @property
    def origin(self):
        """Origin aut-num of this route."""
        try:
            return self["origin"].split()[0]
        except BaseException:
            pass

    @property
    def primary_key(self):
        return "{}{}".format(self.ip_network, self.origin)

    @property
    def lower_maintainers(self):
        """List of maintainers for more-specific objects."""
        return list(self.get("mnt-lower"))

    @property
    def route_maintainers(self):
        """List of maintainers for matching route objects."""
        return list(self.get("mnt-routes"))

    @property
    def primary_key_fields(self):
        return [self.object_class, "origin"]


class AutNumObject(NicObject):
    """Object describing an autonomous system in a NIC database."""
    @property
    def lower_maintainers(self):
        return list(self.get("mnt-lower"))

    @property
    def route_maintainers(self):
        return list(self.get("mnt-routes"))

    def __int__(self):
        return parse_asn(self.object_key)


object_classes = {
    "as-block",
    "as-set",
    "aut-num",
    "domain",
    "filter-set",
    "inet-rtr",
    "inet6num",
    "inetnum",
    "irt",
    "key-cert",
    "mntner",
    "organisation",
    "peering-set",
    "person",
    "poem",
    "poetic-form",
    "role",
    "route-set",
    "route",
    "route6",
    "rtr-set"}
class_synonyms = [{"dns", "domain"}]
primary_key_rules = {}
object_class_types = {
    "route": RouteObject,
    "route6": RouteObject,
    "inetnum": InetnumObject,
    "inet6num": InetnumObject,
    "person": HandleObject,
    "role": HandleObject,
    "as-block": ASBlockObject,
    "aut-num": AutNumObject,
}


class NicDatabaseMixin(object):
    """Mixin which turns a normal database into a NIC database."""

    def __init__(self):
        self.object_classes = object_classes
        self.class_synonyms = class_synonyms
        self.primary_key_rules = primary_key_rules
        self.object_class_types = object_class_types

    def object_class_type(self, object_class):
        try:
            return self.object_class_types[self.primary_class(object_class)]
        except KeyError:
            return NicObject

    def create_object(self, data, object_class=None):
        if object_class is None:
            object_class = data[0][0]
        return self.object_class_type(object_class)(data)

    @property
    def database_name(self):
        return self.manifest.object_key

    @database_name.setter
    def database_name(self, new_name):
        self.manifest.object_key = new_name

    @property
    def serial(self):
        return self.manifest.getfirst("serial", default=0)

    @serial.setter
    def serial(self, new_serial):
        self.manifest["serial"] = new_serial


class FileDatabase(lglass.database.Database, NicDatabaseMixin):
    """NIC database instance that fetches from a directory structure."""

    _manifest = None

    def __init__(self, path, read_only=False, case_insensitive=True):
        NicDatabaseMixin.__init__(self)
        self._path = path
        self.read_only = read_only
        self.case_insensitive = case_insensitive

    def _build_path(self, object_class, object_key=None):
        if object_key is None:
            return os.path.join(self._path, object_class)
        if self.case_insensitive is True:
            object_key = object_key.lower()
        return os.path.join(
            self._path,
            object_class,
            object_key.replace(
                "/",
                "_"))

    def lookup(self, classes=None, keys=None):
        if classes is None:
            classes = self.object_classes
        elif isinstance(classes, str):
            classes = {self.primary_class(classes)}
        else:
            classes = map(self.primary_class, classes)
        for cls in classes:
            try:
                yield from self._lookup_class(cls, keys)
            except FileNotFoundError:
                pass

    def _lookup_class(self, object_class, object_keys):
        if isinstance(object_keys, str):
            if object_keys in {'.', '..'}:
                return
            object_keys = object_keys.replace("_", "/")
            try:
                os.stat(self._build_path(object_class, object_keys))
                yield (object_class, object_keys)
            except FileNotFoundError:
                pass
            return
        try:
            keys_iter = iter(object_keys)
            for key in keys_iter:
                key = key.replace("_", "/")
                try:
                    os.stat(self._build_path(object_class, key))
                    yield (object_class, key)
                except FileNotFoundError:
                    pass
            return
        except TypeError:
            pass
        for key in os.listdir(self._build_path(object_class)):
            if key[0] == '.':
                continue
            key = key.replace("_", "/")
            if lglass.database.perform_key_match(object_keys, key):
                yield (object_class, key)

    def fetch(self, object_class, object_key):
        object_class = self.primary_class(object_class)
        try:
            path = self._build_path(object_class, object_key)
            with open(path) as fh:
                obj = self.object_class_type(object_class).from_file(fh)
            if obj.last_modified is None:
                st = os.stat(path)
                obj.last_modified = st.st_mtime
            if obj.source is None and self.database_name is not None:
                obj.source = self.database_name
            return obj
        except (FileNotFoundError, IsADirectoryError):
            raise KeyError(repr((object_class, object_key)))
        except ValueError as verr:
            raise ValueError((object_class, object_key), *verr.args)

    def save(self, obj, **options):
        if self.read_only:
            raise ValueError
        if isinstance(obj, list):
            obj = self.create_object(obj)
        object_class = self.primary_class(obj.object_class)
        object_key = self.primary_key(obj).replace("/", "_")
        try:
            os.mkdir(os.path.join(self._path, object_class))
        except FileExistsError:
            pass
        save_obj = NicObject(obj.data)
        remove_last_modified = self.database_name in save_obj.get(
            "source") or not save_obj.get("source")
        if remove_last_modified:
            save_obj.remove("last-modified")
        if save_obj.source is not None and save_obj.source == self.database_name:
            save_obj.remove("source")
        path = self._build_path(object_class, object_key)
        with open(path, "w") as fh:
            fh.write("".join(save_obj.pretty_print(**options)))
        if isinstance(obj, NicObject) and obj.last_modified is not None:
            st = os.stat(path)
            mtime = obj.last_modified_datetime.timestamp()
            os.utime(path, times=(st.st_atime, mtime))

    def save_manifest(self):
        if self.read_only:
            raise ValueError
        mf = self.manifest
        with open(os.path.join(self._path, "MANIFEST"), "w") as fh:
            fh.write("".join(mf.pretty_print()))

    def delete(self, obj):
        if self.read_only:
            raise ValueError
        object_class = self.primary_class(obj.object_class)
        object_key = self.primary_key(obj).replace("/", "_")
        os.unlink(self._build_path(object_class, object_key))

    def __contains__(self, obj):
        primary_spec = self.primary_spec(obj)
        return os.path.exists(self._build_path(*primary_spec))

    def close(self):
        pass

    @property
    def manifest(self):
        if self._manifest is not None:
            return self._manifest
        try:
            with open(os.path.join(self._path, "MANIFEST")) as fh:
                obj = NicObject.from_file(fh)
        except FileNotFoundError:
            obj = NicObject([("database", os.path.basename(self._path))])
        self._manifest = obj
        return obj

__all__ = ("NicObject", "HandleObject", "InetnumObject", "ASBlockObject",
        "RouteObject", "AutNumObject", "NicDatabaseMixin", "FileDatabase")
