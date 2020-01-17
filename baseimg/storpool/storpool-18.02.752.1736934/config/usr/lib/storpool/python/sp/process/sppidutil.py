"""Provides some storpool-process recognising machanisms and functions that
report information about storpool processes.
"""

import glob
import re


from sp.process import pidutil
from sp.util import re_extensions
from sp.util.backports import subprocess
from sp.util import misc as utils


def read_sp_pids():
    """Returns a pid-service dictionary of the storpool processes as they can
    be read from /var/run/
    """
    sp_pids = {}
    for path in glob.glob('/var/run/storpool_*.pid'):
        service = path[18:-8] if path.endswith('.bin.pid') else path[18:-4]
        with open(path, 'r') as pidf:
            pid = int(pidf.readlines()[0])
        sp_pids[pid] = service
    return sp_pids


KNOWN_COMM_PREFIXES = {
    'storpool_bridge': 'bridge',
    'storpool_server': 'server',
    'storpool_mgmt': 'mgmt',
    'storpool_beacon': 'beacon',
    'storpool_iscsi': 'iscsi',
    'storpool_block': 'block',
    'sprdma': 'rdma',
    'storpool_nvmed': 'nvmed',
    'storpool_contro': 'controller',
    'storpool_stat': 'stat',
}


def comm_recognise(pid):
    """Tries to recognise if the process is a storpool service only bu its
    comm value. Returns a string, indicating the storpool service or 'unknown'
    if the process cannot be distinguished.
    May return 'dead' if the process is already inexistant.
    """
    try:
        comm = pidutil.get_comm(pid)
    except IOError:
        return 'dead'
    for known_prefix in KNOWN_COMM_PREFIXES:
        if comm.startswith(known_prefix):
            return KNOWN_COMM_PREFIXES[known_prefix]
    return 'unknown'


def recognise(pids):
    """Tries to recognise if the process is a storpool service.
    Returns a string, indicating the storpool service or 'unknown' if the
    process cannot be distinguished. May return 'dead' if the process is
    already inexistant.
    """
    sp_pids = read_sp_pids()

    def _recognise_one(pid):
        if pid <= 1:
            return 'unknown'
        comm = comm_recognise(pid)
        if pid in sp_pids and comm != 'unknown' and comm != 'dead':
            # should prevent old pid + pid collision
            return sp_pids[pid]
        if comm != 'unknown':
            return comm
        return _recognise_one(pidutil.get_parent(pid))

    return dict([(pid, _recognise_one(pid)) for pid in pids])


def sp_pids_info():
    """Returns a four-tuple of (pid, status, cpuset cgroup, memory cgroup)
    for all running storpool processes.
    """
    def sp_nfo((pid, status)):
        """Returns a the four-tuple for a given (pid, status) pair.
        Return None if OSError occures while reading the cgroups config(assuming
        the process died).
        """
        if status not in KNOWN_COMM_PREFIXES.values():
            return None
        try:
            return (pid, status, pidutil.cgroup(pid, 'cpuset'), pidutil.cgroup(pid, 'memory'))
        except OSError:
            return None
    return [nfo for nfo in map(sp_nfo, recognise(pidutil.all_pids()).items()) if nfo is not None]


CGROUPS_REGEX = re.compile(r'''SP_(?P<service>\w+)_CGROUPS \s* = \s*
                           -g \s* cpuset:(?P<cpuset>[\w/.]+) \s+
                           -g \s* memory:(?P<memory>[\w/.]+)''', re.X)


def sp_cg_config():
    """Returns a service-(controller-group) dictionary of the configured cgroups
    for each service in the storpool.conf
    """
    config = {}
    showconf_binary = '/usr/sbin/storpool_showconf'
    assert utils.is_exe(showconf_binary)
    lines = subprocess.check_output([showconf_binary] + ['CGROUPS']).split('\n')
    for mcg in re_extensions.matches(CGROUPS_REGEX, lines):
        grps = mcg.groupdict()
        service = grps.pop('service').lower()
        if service.startswith('server') and len(service) == 7:
            service = 'server_{0}'.format(service[-1])
        config[service] = grps
    return config
