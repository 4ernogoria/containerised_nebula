"""Provides utilities for converting and summating limit strings."""

from __future__ import division


def limit_str_to_mb(limit):
    """Returns the size in MB of a limit string([0-9]+[MG])."""
    size = int(limit[:-1])
    mult = 1024 if limit[-1] == 'G' else 1
    return size * mult


def sum_limit_strs(*args):
    """Returns a limit string that is the sum of the given limit strings."""
    mbs = 0
    for limit in args:
        mbs += limit_str_to_mb(limit)
    if mbs % 1024 == 0:
        return "{0}G".format(mbs // 1024)
    return "{0}M".format(mbs)


def valid_limit_str(limit):
    """Indicates whether a string is valid limit string."""
    if limit[-1] not in ('M', 'G'):
        return False
    if not limit[:-1].isdigit():
        return False
    return True


def limit_to_gb_str(lim):
    """Creates limit string from integer or floating point limit value in GB."""
    if (isinstance(lim, float) and lim.is_integer()) or isinstance(lim, int):
        return '{0}G'.format(int(lim))
    else:
        return '{0}M'.format(int(lim * 1024))
