"""
Provides functionalities/information for some storpool-specific
memory aspects of the machine.
"""

from __future__ import division

import collections
import errno
import os

from storpool import spconfig

from sp import cpuinfo
from sp import installed
from sp import messages as m
from sp import service as svc
from sp.cgroups import hierarchy as cgh
from sp.disk import disklist as spdisk
from sp.util import decorators as spd
from sp.util import misc as utils
from sp.util import re_extensions as extre
from sp.util.file import readers, writers


NUMA_HUGEPAGES_NR_FILE_TMPL = '/sys/devices/system/node/node{n}/hugepages' \
                              '/hugepages-{s}kB/nr_hugepages'
HUGEPAGES_SZ_MB = 2
HUGEPAGES_SZ_KB = HUGEPAGES_SZ_MB * 1024
HUGEPAGES_SZ_B = HUGEPAGES_SZ_KB * 1024


def sp_numa(default=None):
    """Get the NUMA node on which the StorPool services will run."""
    numa = default
    cpu_info = cgh.get().cpuset_info()
    mems = cpu_info.get('storpool.slice', {}).get('cpuset.mems')
    if mems:
        numa = mems[0]
    return numa


def check_hugepage_sz(numa=0):
    """Make sure that the specified NUMA node supports 2MB hugepages."""
    return os.path.isfile(
        NUMA_HUGEPAGES_NR_FILE_TMPL.format(n=numa, s=HUGEPAGES_SZ_KB))


def get_nr_hugepages(numa=0):
    """
    Returns the number of hugepages on the specified numa node
    (default 0).
    """
    return int(readers.file_content(
        NUMA_HUGEPAGES_NR_FILE_TMPL
        .format(n=numa, s=HUGEPAGES_SZ_KB)).strip())


def set_nr_hugepages(nr_hugepages, numa=0):
    """Sets the number of hugepages on the specified numa node(default 0)."""
    writers.write_file(
        NUMA_HUGEPAGES_NR_FILE_TMPL.format(n=numa, s=HUGEPAGES_SZ_KB),
        str(nr_hugepages))
    m.msg("{h} hugepages written for {n} numa".format(h=nr_hugepages, n=numa))
    reserved = get_nr_hugepages(numa)
    return reserved >= nr_hugepages


def sp_supports_hugepages():
    """
    Indicates wheter current version of StorPool needs
    hugepages configuration.
    """
    return utils.sp_mver() >= (18, 2)


def sp_nvme_devices():
    """
    Reads the storpool.conf and returns a list of pci addresses for
    StorPool nvme devices.
    """
    try:
        cfg = spconfig.SPConfig()
    except spconfig.SPConfigException:
        return []
    nvme_pci_ids = cfg.get('SP_NVME_PCI_ID', '')
    return nvme_pci_ids.strip().split()


def nvme_block_devices_from_pci(pci_address):
    """
    Return the names of the disks and partitions on the specified
    NVME device.
    """
    nvme_base = '/sys/bus/pci/devices/{0}/nvme'.format(pci_address)
    if not os.path.isdir(nvme_base):
        return []
    devices = []
    for nvme_ctrl in os.listdir(nvme_base):
        ctrl_path = os.path.join(nvme_base, nvme_ctrl)
        disks = [e for e in os.listdir(ctrl_path)
                 if e.startswith(nvme_ctrl + 'n')]
        devices.extend(disks)
        for disk in disks:
            disk_path = os.path.join(ctrl_path, disk)
            partitions = [e for e in os.listdir(disk_path)
                          if e.startswith(disk + 'p')]
            devices.extend(partitions)
    return devices


def sp_nvme_devices_partitions():
    """Return a list of partitions on NVME devices."""
    sp_nvmes = sp_nvme_devices()
    sp_dev_list = list(set(
        disk['device'] for disk in spdisk.all_disks(skip_types=())))

    def _dev(match):
        """Return the device name, possibly with a partition suffix."""
        dev = match.group('pci')
        part = match.group('partition')
        if part is not None:
            return '{dev}-p{part}'.format(dev=dev, part=part)
        return dev

    nvmed_binds = [_dev(rem) for rem in extre.matches(spdisk.SP_NVME_RE,
                                                      sp_dev_list)]
    regular_devices = utils.list2d_flatten(
        map(nvme_block_devices_from_pci, sp_nvmes))
    regular_devices = [dev for dev in regular_devices
                       if '/dev/{0}'.format(dev) in sp_dev_list]
    return nvmed_binds + regular_devices


HUGEPAGE_SERVICES = set(['block', 'beacon', 'mgmt', 'iscsi', 'bridge',
                         'server'] +
                        svc.strip_prefix(installed.EXTRA_SERVERS))
HUGEPAGES_PER_SERVICE = 16
HUGEPAGES_MEMORY_PER_SERVICE_MB = HUGEPAGES_PER_SERVICE * HUGEPAGES_SZ_MB
HUGEPAGES_MEMORY_PER_SP_NVME_DEV_PART_MB = 12

ExpectedHugePagesFile = collections.namedtuple('ExpectedHugePagesFile', [
    'service',
    'path',
    'expected_pages',
    'current_pages',
])

HugePagesNVME = collections.namedtuple('HugePagesNVME', [
    'phys',
    'disks',
])

HP_SPECIAL_NAMES = {
    'nvmed': 'physmem.nvmed',
    'nvmed_disks': 'physmem.disks.nvmed',
}


class ExamineError(Exception):
    """
    An error that occurred while examining the current configuration of
    the system and the StorPool hugetlbfs directory.
    """


@spd.static_vars(path=None)
def sp_hugepages_path(path=None):
    """
    Determines the real path to the hugetlbfs directory where
    the StorPool hugepages files are allocated.
    """
    if sp_hugepages_path.path is not None:
        return sp_hugepages_path.path

    if path is None:
        if os.path.isdir('/run'):
            path = '/run/storpool/hugetlb'
        else:
            path = '/var/run/storpool/hugetlb'
    sp_hugepages_path.path = os.path.realpath(path)
    return sp_hugepages_path.path


def get_service_allocated(name, expected=0, path=None):
    """
    Returns the number of hugepages currently allocated for the specified
    service in the StorPool hugetlbfs directory.
    """
    path = sp_hugepages_path(path)
    fpath = path + os.sep + HP_SPECIAL_NAMES.get(name, 'storpool_' + name)
    try:
        data = os.stat(fpath)
        if data.st_size % HUGEPAGES_SZ_B:
            raise ExamineError(
                'The {path} file has an unexpected size of {size}'
                .format(path=fpath, size=data.st_size))
        current = int(data.st_size / HUGEPAGES_SZ_B)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise
        current = None

    return ExpectedHugePagesFile(
        service=name,
        path=fpath,
        current_pages=current,
        expected_pages=expected,
    )


def get_service_hp(name, path=None, nvme_hp_needed=None):
    """
    Returns the number of currently configured and expected pages
    to be allocated for the specified service.
    """
    if name == 'nvmed':
        expected_pages = nvme_hp_needed.phys
    elif name == 'nvmed_disks':
        expected_pages = nvme_hp_needed.disks
    else:
        expected_pages = HUGEPAGES_PER_SERVICE

    return get_service_allocated(name, expected=expected_pages, path=path)


def get_services_hp(services, path=None, nvme_hp_needed=None):
    """
    Returns the number of currently allocated and expected hugepages for
    the specified services or for the default list of StorPool services.
    """
    services_set = set(services) & HUGEPAGE_SERVICES
    if 'nvmed' in services:
        services_set = services_set | set(['nvmed', 'nvmed_disks'])

    return dict((
        svc, get_service_hp(svc, path, nvme_hp_needed)
    ) for svc in services_set)


def nvme_hugepages_split():
    """
    Returns the number of hugepages needed to use the specified
    NVME devices: the first element of the tuple is for the devices
    themselves (the memory used by the storpool_nvmed service) and
    the second one is for the StorPool data disks on them (the memory
    used by the storpool_server service).
    """
    devices = len(sp_nvme_devices())
    partitions = len(sp_nvme_devices_partitions())
    assert devices != 0 or partitions == 0, \
        'Found {cnt} NVME partitions, but no devices!'.format(cnt=partitions)
    mb_needed = HugePagesNVME(
        phys=2 if devices > 0 else 0,
        disks=partitions * HUGEPAGES_MEMORY_PER_SP_NVME_DEV_PART_MB,
    )
    return HugePagesNVME(
        phys=int(mb_needed.phys / HUGEPAGES_SZ_MB),
        disks=int(mb_needed.disks / HUGEPAGES_SZ_MB),
    )


def nvme_hugepages_needed():
    """
    Returns the total number of hugepages needed to use the specified
    NVME devices.
    """
    hp_needed = nvme_hugepages_split()
    return hp_needed.phys + hp_needed.disks


def all_hugepages_memory_mb():
    """
    Returns the total number of hugepages of all sizes currently
    configured on all NUMA nodes.
    """
    def _read(filen):
        return int(readers.file_content(filen).strip()) \
            if os.path.isfile(filen) else 0

    def _numa_mb(numa):
        psizes = [2048, 1048576]
        files = [NUMA_HUGEPAGES_NR_FILE_TMPL.format(n=numa, s=psize)
                 for psize in psizes]
        return sum(c * (ps // 1024)
                   for c, ps in zip(map(_read, files), psizes))

    return sum(_numa_mb(n) for n in range(cpuinfo.get().numa_nodes()))
