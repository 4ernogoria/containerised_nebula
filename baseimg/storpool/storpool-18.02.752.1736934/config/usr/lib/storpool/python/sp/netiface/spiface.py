"""Provides information for some storpool-specific network properties of the machine."""

from sp import messages as m
from sp.netiface import ifaceutil
from sp.util import misc as utils
from sp.util.backports import subprocess


try:
    from storpool import spconfig

    def ifaces_from_conf():
        """Return list of storpool interfaces as read from the python bidnings
        for the configuration. V2 variables are taken with priority.
        """
        cfg = spconfig.SPConfig()
        ifaces = []
        for confvar in ('SP_IFACE1_CFG', 'SP_IFACE2_CFG'):
            if confvar in cfg:
                ifaces.append(cfg[confvar].split(':')[2])
        if not ifaces and 'SP_IFACE' in cfg:
            ifaces = cfg['SP_IFACE'].split(',')
            ifaces = [iface.split('=')[0] for iface in ifaces]
        return ifaces

except ImportError:
    m.msg("Could not import the StorPool Python bindings.")

    def ifaces_from_conf():
        """Return list of storpool interfaces as read from storpool_showconf.
        V2 variables are taken with priority.
        """
        assert utils.which('storpool_showconf') is not None
        ifacesv2_1 = subprocess.check_output(['storpool_showconf', '-en', 'SP_IFACE1_CFG'])
        if ifacesv2_1 != '\n':
            raw = [ifacesv2_1.split(':')[2]]
            ifacesv2_2 = subprocess.check_output(['storpool_showconf', '-en', 'SP_IFACE2_CFG'])
            if ifacesv2_2 != '\n':
                raw.append(ifacesv2_2.split(':')[2])
            return raw
        ifacesv1 = subprocess.check_output(['storpool_showconf', '-en', 'SP_IFACE'])[:-1]
        ifacesv1 = ifacesv1.split(',')
        ifacesv1 = [iface.split('=')[0] for iface in ifacesv1]
        return ifacesv1


def first_sp_iface():
    """Returns the raw interface for storpool which is on the numa node with
    the smallest id.
    """
    def _numa_node_for(iface):
        try:
            return ifaceutil.numa_node_for(iface)
        except (OSError, IOError):
            return -1

    ifs = sorted(sp_ifaces(), key=_numa_node_for)
    # check for weird config
    numas = [n for n in map(_numa_node_for, ifs) if n != -1]
    if len(set(numas)) > 1:
        m.warn_msg("Network interfaces for StorPool: {0} are on different numa nodes".format(ifs))
    if not ifs:
        m.exit_msg('Could not find any raw interfaces for StorPool')
    return ifs[0]


def sp_ifaces():
    """Returns the list of raw interfaces for StorPool."""
    raw_ifaces = set()
    for conf_iface in ifaces_from_conf():
        raw_ifaces.update(ifaceutil.raw_ifaces_for(conf_iface))
    return list(raw_ifaces)


def sp_has_acc():
    """Indicates whether current version of StorPool has interface acceleration."""
    return utils.sp_mver() >= (18, 2)


HDWRACC_DRIVERS = ['mlx4_core', 'mlx5_core', 'ixgbe', 'i40e', 'bnx2x']


def has_acc(iface):
    """Indicates whether current version of StorPool has interface acceleration
    and the given interface has hardware acceleration compatible driver."""
    return sp_has_acc() and ifaceutil.driver_for(iface) in HDWRACC_DRIVERS
