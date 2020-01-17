"""Reads and provides information about the machine network inerfaces."""

import glob
import os
import re


from sp.util import misc as utils
from sp.util import re_extensions as extre
from sp.util import decorators as spd
from sp.util.file import parsers


BASE_PATH_T = '/sys/class/net/{0}'
VLAN_PATH_T = '/proc/net/vlan/{0}'


def raw_ifaces_for(iface):
    """Returns a list of the raw interfaces for the given interface."""
    def _lower_or_same(iface):
        if not is_iface(iface):
            return []
        low = lower(iface)
        return low if low else [iface]
    ifaces = []
    lower_ifaces = [iface]
    while ifaces != lower_ifaces:
        ifaces = lower_ifaces
        lower_ifaces = utils.list2d_flatten(map(_lower_or_same, lower_ifaces))
    return [iface for iface in ifaces if is_raw(iface)]


def vlan_path_for(iface):
    """Contructs a vlan path for the interface."""
    return VLAN_PATH_T.format(iface)


def base_path_for(iface):
    """Contructs a path for the base interface directory."""
    return BASE_PATH_T.format(iface)


def bonding_path_for(iface):
    """Constructs path for the bonding file of the interface."""
    return os.path.join(base_path_for(iface), 'bonding')


def bridge_path_for(iface):
    """Constructs path for the bridge file of the interface."""
    return os.path.join(base_path_for(iface), 'bridge')


def device_path_for(iface):
    """Constructs path for the device file of the interface."""
    return os.path.join(base_path_for(iface), 'device')


def _globs(iface, rel_glob):
    glob_path = os.path.join(base_path_for(iface), rel_glob)
    return glob.glob(glob_path)


def _lower_paths_for(iface):
    return _globs(iface, 'lower_*')


def _slave_paths_for(iface):
    return _globs(iface, 'slave_*')


def _brif_paths_for(iface):
    return _globs(iface, 'brif/*')


def is_iface(iface):
    """Indicates whether the given interface exists."""
    return os.path.exists(base_path_for(iface))


def is_device(iface):
    """Indicates whether the given interface is a device."""
    return os.path.islink(device_path_for(iface))


def is_bond(iface):
    """Indicates whether the given interface is a bond."""
    return os.path.isdir(bonding_path_for(iface))


def is_bridge(iface):
    """Indicates whether the given interface is a bridge."""
    return os.path.isdir(bridge_path_for(iface))


def is_vlan(iface):
    """Indicates whether the given interface is a vlan."""
    return os.path.isfile(vlan_path_for(iface))


def readlinks(paths):
    """Apply readlink to all links in the list. Other items are left unchanged."""
    return [os.readlink(p) if os.path.islink(p) else p for p in paths]


def basenames(paths):
    """Return list of basenames for the paths."""
    return map(os.path.basename, paths)


def lower(iface):
    """Return list of lower interfaces for the given interface.
    If none return None.
    """
    if _lower_paths_for(iface):
        return basenames(readlinks(_lower_paths_for(iface)))
    elif is_bond(iface):
        return basenames(readlinks(_slave_paths_for(iface)))
    elif is_bridge(iface):
        return [dev for dev in basenames(_brif_paths_for(iface))
                if is_bond(dev) or is_vlan(dev) or is_device(dev)]
    elif is_vlan(iface):
        with open(vlan_path_for(iface), 'r') as vlanf:
            lines = vlanf.readlines()
        devs = extre.matches(re.compile(r"^Device: (?P<dev>.+)$"), lines)
        return [dev.group('dev') for dev in devs]
    return None


def is_raw(iface):
    """Indicates whether the given interface is a raw interface."""
    return is_device(iface) and \
           not is_bond(iface) and \
           not is_vlan(iface) and \
           not is_bridge(iface)


def numa_node_path_for(iface):
    """Constructs path for the numa node file for the given interface."""
    return os.path.join(device_path_for(iface), 'numa_node')


def _read_numa_node_from(numa_node_file):
    with open(numa_node_file, 'r') as nnf:
        lines = nnf.readlines()
    return int(lines[0])


def numa_node_for(iface):
    """Returns the numa node for the interface."""
    return _read_numa_node_from(numa_node_path_for(iface))


def driver_for(iface):
    """Returns the driver model for the interface."""
    driver_path = os.path.join(device_path_for(iface), 'driver')
    if os.path.islink(driver_path):
        return os.path.basename(os.readlink(driver_path))
    return None


def local_cpulist_path_for(iface):
    """Constructs a path for the local cpulist of the given interface."""
    return os.path.join(device_path_for(iface), 'local_cpulist')


def _read_local_cpus_from(local_cpulist_file):
    with open(local_cpulist_file, 'r') as lcpulf:
        lines = lcpulf.readlines()
    return parsers.sranges_to_list(lines[0])


@spd.static_vars(cache={})
def localcpus_for(iface, reread=False):
    """Returns a list of the local cpus for the gien interface.
    List will be cached for each different interface.
    Setting the reread flag to True, will drop the cache and reread the cpus.
    """
    if iface in localcpus_for.cache and not reread:
        return localcpus_for.cache[iface]
    local_cpulist_file = local_cpulist_path_for(iface)
    localcpus_for.cache[iface] = _read_local_cpus_from(local_cpulist_file)
    return localcpus_for.cache[iface]
