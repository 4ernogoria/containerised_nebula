"""Provides some filters for easy filtering of cgroups by name."""

def is_sp_cgroup(grp):
    """Indicates whether the group is storpool group or subgroup."""
    return grp.startswith('storpool.slice') or grp == 'mgmt.slice'


def is_sp_subgroup(grp):
    """Indicates whether the group is storpool subgroup(strict)."""
    return grp.startswith('storpool.slice/')


def is_not_sp_cgroup(grp):
    """Indicates whether the group is not storpool group or storpool subgroup."""
    return not is_sp_cgroup(grp)


def is_sp_or_root(grp):
    """Indicates whether the group is storpool group or root cgroup."""
    return grp == '.' or grp == 'storpool.slice'


def is_direct_root_child(grp):
    """Indicates whether the group is direct root child."""
    return '/' not in grp and grp != '.'


def is_not_sp_direct_root_child(grp):
    """Indicates whether the group is direct root child, but it is not storpool group."""
    return is_direct_root_child(grp) and grp != 'storpool.slice'
