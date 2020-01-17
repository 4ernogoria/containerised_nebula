"""Provides functions for easy access to common process properties."""

import os
import re


from sp.util import re_extensions as extre
from sp.util.file import readers


def get_comm(pid):
    """Returns the comm of the given pid."""
    return readers.lines('/proc/{0}/comm'.format(pid))[0]


STAT_RE = re.compile(r'(?P<pre> [^)]*? ) \s+ (?P<comm> \( [^)]* \) ) \s+ (?P<after> .* )', re.X)


def get_stat(pid):
    """Returns the stat of the given pid."""
    line = readers.lines('/proc/{0}/stat'.format(pid))[0].rstrip()
    gdict = re.match(STAT_RE, line).groupdict()
    return gdict['pre'].split() + [gdict['comm']] + gdict['after'].split()


def get_parent(pid):
    """Returns the ppid of the given pid."""
    return int(get_stat(pid)[3])


def get_status(pid):
    """Returns the status of the given pid."""
    return get_stat(pid)[2]


TGID_RE = re.compile(r"Tgid:\s+(?P<tgid>\d+)")


def get_tgid(pid):
    tgid_matches = extre.matches(TGID_RE, readers.lines('/proc/{0}/status'.format(pid)))
    if not tgid_matches:
        return None
    return int(tgid_matches[0].group('tgid'))


def get_cmdline(pid):
    return readers.lines('/proc/{0}/cmdline'.format(pid))[0]


def exists(pid):
    """Indicates whether the given pid exists."""
    return os.path.isdir('/proc/{0}'.format(pid))


def cgroups(pid):
    """Returns a cgroups controller-cgroup dictionary for the given pid."""
    raw = readers.lines('/proc/{0}/cgroup'.format(pid))
    return dict([line.rstrip().split(':')[1:3] for line in raw])


def cgroup(pid, controller):
    """Returns the cgroup for the given controller of the given pid."""
    group = cgroups(pid)[controller]
    return '.' if group == '/' else group[1:]


def ancestors_of(pid):
    """Returns list of acestors(pids) of the given pid in the process tree."""
    ancestors = []
    while get_parent(pid) != 0:
        ancestors.append(get_parent(pid))
        pid = get_parent(pid)
    return ancestors


def all_pids(no_zombies=True):
    """Returns a list of all pids.
    If no_zombies parameter is set to True, zombie processes will be filtered.
    """
    def _alive_not_zombie(pid):
        try:
            return get_status(pid) != 'Z'
        except (OSError, IOError):
            return False

    pids = [int(d) for d in os.listdir('/proc') if d.isdigit()]
    if no_zombies:
        pids = [pid for pid in pids if _alive_not_zombie(pid)]
    return pids
