"""Provides utilities to convert python lists to ranges strings and vice versa."""

from sp.util import misc as utils


def srange_to_list(srange):
    """Create a list of integers from range string(e.g. 10-15)."""
    if not srange.rstrip():
        return []
    if '-' not in srange:
        return [int(srange)]
    start, end = map(int, srange.split('-'))
    return list(range(start, end + 1))


def sranges_to_list(sranges):
    """Create a list of integers from ranges string(e.g. 10-15,20-25)."""
    cpus_2dl = map(srange_to_list, sranges.split(','))
    return utils.list2d_flatten(cpus_2dl)


def _conslist_to_srange(ccpul):
    if len(ccpul) == 1:
        return str(ccpul[0])
    return '{0}-{1}'.format(ccpul[0], ccpul[-1])


def list_to_sranges(cpul):
    """Create ranges string(e.g. 10-15,20-25 from list of integers.)"""
    cpul = sorted(cpul)
    splits = [i for i in range(0, len(cpul) + 1)
              if i == 0 or i == len(cpul) or cpul[i - 1] != cpul[i] - 1]
    cpul2d = [cpul[b:e] for b, e in zip(splits, splits[1:])]
    return ','.join(map(_conslist_to_srange, cpul2d))


def parse_range_file(content):
    """Create list of numbers from the string content of a ranges list file."""
    if not content or content == '\n':
        return None
    return sranges_to_list(content)


def parse_pids_file(content):
    """Creates list of pids from the string content of a pid list file."""
    return map(int, [pid for pid in content.rstrip().split('\n') if pid])
