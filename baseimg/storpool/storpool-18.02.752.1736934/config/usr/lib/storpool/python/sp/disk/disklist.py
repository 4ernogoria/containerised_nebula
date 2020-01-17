"""Provides information about the StorPool data disks on the machine."""

from __future__ import division

import os
import re

from sp.util import misc as utils
from sp.util.backports import subprocess
from sp.util import decorators as spd


class DiskListError(Exception):
    """ An error that occurred while listing the StorPool data disks. """

    def __init__(self, action, error):
        """ Initialize an error object with the specified data. """
        super(DiskListError, self).__init__(self._get_str(action, error))
        self.action = action
        self.error = error

    @staticmethod
    def _get_str(action, error):
        """ Describe an error that occurred. """
        return 'Could not list the StorPool data disks: {action}: {error}'. \
            format(action=action, error=error)

    def __repr__(self):
        """ Provide a Python-esque representation of the error object. """
        return '{name}(action={action}, error={error})'.format(
            name=type(self).__name__,
            action=repr(self.action),
            error=repr(self.error))

    def __str__(self):
        """ Provide a human-readable representation of the error. """
        return self._get_str(self.action, self.error)


def initdisk_list():
    """Returns the output of storpool_initdisk --list"""
    initdisk_binary = os.environ.get('STORPOOL_INITDISK',
                                     '/usr/sbin/storpool_initdisk')
    if not utils.is_exe(initdisk_binary):
        return ''

    try:
        return subprocess.check_output([initdisk_binary, '--list'],
                                       stderr=None)
    except (IOError, OSError) as err:
        raise DiskListError(
            action='exec {path}'.format(path=initdisk_binary),
            error=err)
    except subprocess.CalledProcessError as err:
        raise DiskListError(
            action='fail {path}'.format(path=initdisk_binary),
            error=err)


def parse_flag(flag):
    """Construct a key-value pair from the raw string for a disk flag."""
    parts = flag.split()
    if len(parts) == 1:
        return (parts[0], True)
    if len(parts) == 2 and parts[0] == 'no':
        return (''.join(parts), True)
    if len(parts) == 2 and parts[0] == 'jmv':
        return ('jmv', parts[1])
    if len(parts) == 3 and parts[0] == 'journal':
        return ('journal', True)
    return None


SP_NVME_RE = re.compile(r'''
    (?P<pci> [0-9a-fA-F]{4,} : [0-9a-fA-F]{2} : [0-9a-fA-F]{2} \. .)
    ( - p (?P<partition> \d+ ))?
''', re.X)


def is_nvme(blockdev):
    """ Is this a StorPool-managed NVME device or partition? """
    return SP_NVME_RE.match(blockdev) is not None


def disk_dict(info):
    """Construct the disk object from the storpool_initisk split line."""
    blockdev = info[0]
    disk_id = int(info[1].split()[-1])  # dont ask...
    version = int(info[2].split()[-1], 16)
    instance = int(info[3].split()[-1])
    cluster = info[4].split()[-1]
    flags = dict([parse_flag(flag) for flag in info[5:]])
    disk = {}
    disk['id'] = disk_id
    disk['device'] = blockdev
    disk['name'] = os.path.basename(disk['device'])
    disk['cluster'] = cluster
    disk['nvme'] = is_nvme(blockdev)
    diskmeta = flags
    diskmeta['instance'] = instance
    diskmeta['version'] = version
    disk['meta'] = diskmeta
    if disk['meta'].get('journal'):
        disk['type'] = 'journal'
    else:
        disk['type'] = 'storpool'
    return disk


@spd.static_vars(disks=None)
def all_disks(reread=False, skip_types=('unknown',)):
    """Parser the output of storpool_initdisk and creates dict objects for each
    disk. Returns list of all disk objects.
    List is cached.
    Specify the reread flag to drop the cache and reread the disk list."""

    def eligible():
        """ Return the disks not excluded by the skip_types parameter. """
        return [disk for disk in all_disks.disks
                if disk['type'] not in skip_types]

    if all_disks.disks is not None and not reread:
        return eligible()

    all_disks.disks = []
    for line in initdisk_list().split('\n'):
        if not line or line == 'Done.':
            continue
        if line.endswith('is not a Storpool data disk.'):
            device = line.split(' ', 1)[0]
            all_disks.disks.append({
                'device': device,
                'type': 'unknown',
                'nvme': is_nvme(device),
            })
            continue
        try:
            all_disks.disks.append(disk_dict(line.split(', ')))
        except (IndexError, ValueError) as err:
            raise DiskListError(
                action='parse {line}'.format(line=repr(line)),
                error=err)

    return eligible()


def cap_bytes(devs_list):
    """Returns disk capacities for the given devices."""
    if not devs_list:
        return {}
    caps = {}
    cmd = ['lsblk'] + devs_list + ['--bytes']
    try:
        lsblk = subprocess.check_output(cmd).split('\n')[1:-1]
    except (IOError, OSError) as err:
        raise DiskListError(
            action='exec {path}'.format(path=cmd[0]),
            error=err)
    except subprocess.CalledProcessError as err:
        raise DiskListError(
            action='fail {path}'.format(path=cmd[0]),
            error=err)
    for entry in lsblk:
        fields = entry.split()
        try:
            name = fields[0]
            cap = int(fields[3])
            caps[name] = cap
        except (IndexError, ValueError) as err:
            raise DiskListError(
                action='parse lsblk {entry}'.format(entry=repr(entry)),
                error=err)
    return caps


def all_disks_with_caps(reread=False):
    """Adds capacity to the disk objects generated by all_disks and returns the
    list with updated disk objects.
    """
    disks = all_disks(reread)
    caps = cap_bytes([disk['device'] for disk in disks])
    for disk in disks:
        if disk['name'] in caps:
            disk['cap'] = caps[disk['name']]
    return disks


def server_instances(reread=False):
    """Returns the number of storpool server intances on the machine, deduced
    from the disk list."""
    instances = set(disk['meta']['instance'] for disk in all_disks(reread))
    if instances:
        return max(instances) + 1
    return 0


ENTRY_GROUPS_BUFFER_COUNT = 5
ENTRIES_ROTATE = 1500


def entries_count(disk):
    """Returns the number of entries for the given disk."""
    cap_m = disk['cap'] // (1024 * 1024)
    cap_m += 10500
    round_to = ENTRY_GROUPS_BUFFER_COUNT * 2 * ENTRIES_ROTATE
    entries = ((cap_m + round_to - 1) // round_to) * round_to
    if 'SSD' in disk['meta']:
        entries *= 4
    return entries
