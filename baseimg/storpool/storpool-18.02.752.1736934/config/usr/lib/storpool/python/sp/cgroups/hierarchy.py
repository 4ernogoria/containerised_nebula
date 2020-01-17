"""Provides classes with common interface to work with the cgroups hierarchy."""

from __future__ import print_function
import collections
import os
import re


from sp.process import pidutil
from sp.util import re_extensions
from sp.util import decorators as spd
from sp.util.file import readers, parsers


CG_MOUNT_RE = re.compile(r'''^cgroup\s+
                             (?P<path>/[\w/]+)\s+
                             cgroup\s+
                             (?P<opts>[\w\,]+)''', re.X)


@spd.static_vars(cache={})
def controller_path(controller, reread=False):
    """Reads /proc/mounts and finds the mount point for the given
    controller(if any). Result for each controller is cached.
    If reread flag is specified, cache for the controller will be dropped and
    mount point will be reread from /proc/mounts.
    """
    if not reread and controller in controller_path.cache:
        return controller_path.cache[controller]

    for match in re_extensions.matches(CG_MOUNT_RE, readers.lines('/proc/mounts')):
        cgpath = match.group('path')
        cgopts = match.group('opts').split(',')
        if controller in cgopts:
            controller_path.cache[controller] = cgpath
    if controller not in controller_path.cache:
        raise ValueError('{0} controller has no mount point'.format(controller))
    return controller_path.cache[controller]


class CGroupsHierarchy(object):
    """Base class for a cgroups hierarchy."""
    options = {
        'memory': {
            'RW': {
                'memory.limit_in_bytes': int,
                'memory.memsw.limit_in_bytes': int,
                'memory.move_charge_at_immigrate': int,
                'memory.use_hierarchy': int,
                'memory.swappiness': int,
            },
            'RO': {
                'memory.usage_in_bytes': int,
                'memory.max_usage_in_bytes': int,
            },
        },
        'cpuset': {
            'RW': {
                'cpuset.mems': parsers.parse_range_file,
                'cpuset.cpus': parsers.parse_range_file,
                'cpuset.cpu_exclusive': int,
            },
            'RO': {},
        },
    }

    def _get_options_for(self, ctrl):
        assert ctrl in CGroupsHierarchy.options
        return dict(self.options[ctrl]['RW'].items() +
                    self.options[ctrl]['RO'].items())

    def groups(self, ctrl):
        """Returns list of cgroups in the given controller."""
        raise NotImplementedError()

    def create_group(self, ctrl, group):
        """Creates a group in the given controller."""
        raise NotImplementedError()

    def remove_group(self, ctrl, group):
        """Removes a group in the given controller."""
        raise NotImplementedError()

    def get_option(self, ctrl, group, option):
        """Reads and returns the value of the specified option in the given group."""
        raise NotImplementedError()

    def set_option(self, ctrl, group, option, value):
        """Sets the value of the specified option in the given group."""
        raise NotImplementedError()

    def group_procs(self, ctrl, group):
        """Return list of pids accounted in the given cgroup."""
        return parsers.parse_pids_file(self.get_option(ctrl, group, 'cgroup.procs'))

    def subgroups(self, ctrl, group):  # including group
        """Returns a list of subroups of the given group,
        INCLUDING the group itself.
        """
        return [grp for grp in self.groups(ctrl) if (grp + '/').startswith(group)]

    def group_exists(self, ctrl, group):
        """Indicates whether the given group exists in the given controller."""
        return group in self.groups(ctrl)

    def get_group_info(self, ctrl, group, options):
        """Contructs an option-value dictionary for the given group and using
        the given options.
        """
        grp_info = {}
        for option, parser in options.items():
            try:
                grp_info[option] = parser(self.get_option(ctrl, group, option))
            except ValueError:
                pass
        return grp_info

    def get_info(self, ctrl, options):
        """Contructs a group-(option-value) dictionary using all groups in the
        given controller.
        """
        info = {}
        for group in self.groups(ctrl):
            if group == 'sysdefault' or group == 'init.scope':  # skip systemd bullshits
                continue
            info[group] = self.get_group_info(ctrl, group, options)
        return info

    def _info(self, group, with_procs):
        options = self._get_options_for(group)
        if with_procs:
            options['cgroup.procs'] = parsers.parse_pids_file
        return self.get_info(group, options)

    def cpuset_info(self, with_procs=False):
        """Returns info for the cpuset controller.
        If with_procs is set to True, will also read the cgroup.procs option.
        """
        return self._info('cpuset', with_procs)

    def memory_info(self, with_procs=False):
        """Returns info for the memory controller.
        If with_procs is set to True, will also read the cgroup.procs option.
        """
        return self._info('memory', with_procs)

    def cpuset_memory_info(self):
        """Return pair of cpuset and memory info. cgroup.procs is included."""
        return self.cpuset_info(True), self.memory_info(True)

    def safe_classify(self, ctrl, group, pid):
        """Failsafe for the classify operation if the process dies just before
        it is moved. All other errors will be reraised.
        """
        try:
            self.set_option(ctrl, group, 'cgroup.procs', '{0}\n'.format(pid))
        except OSError as err:
            if pidutil.exists(pid):
                raise err


class CGroupsHierarchyReal(CGroupsHierarchy):
    """A real cgroups hierarchy, making changes to the machine."""
    def _get_option_path(self, ctrl, group, option):
        if not self.group_exists(ctrl, group):
            raise ValueError("{0} is not a valid group in the {1} controller"
                             .format(group, ctrl))
        opath = os.path.join(controller_path(ctrl), group, option)
        if not os.path.isfile(opath):
            raise ValueError("{0} is not a valid option for the {1} group in the {2} controller"
                             .format(option, group, ctrl))
        return opath

    def group_exists(self, ctrl, group):  # for optimization
        return os.path.isdir(os.path.join(controller_path(ctrl), group))

    def groups(self, ctrl):
        ctrl_path = controller_path(ctrl)
        return [os.path.relpath(grp, ctrl_path) for grp, _, __ in os.walk(ctrl_path)]

    def create_group(self, ctrl, group):
        os.mkdir(os.path.join(controller_path(ctrl), group))

    def remove_group(self, ctrl, group):
        os.rmdir(os.path.join(controller_path(ctrl), group))

    def get_option(self, ctrl, group, option):
        return readers.file_content(self._get_option_path(ctrl, group, option))

    def set_option(self, ctrl, group, option, value):
        opath = self._get_option_path(ctrl, group, option)
        with open(opath, 'w') as fhandle:
            fhandle.write(value)


class CGroupsHierarchyMock(CGroupsHierarchy):
    """A fake/mock of the cgroups hierarchy, that does not make changes to the
    machine. Actions are printed to the standart output.
    """
    def __init__(self):
        cpu_opts = self._get_options_for('cpuset')
        for key in cpu_opts:
            cpu_opts[key] = lambda x: x
        cpu_opts['cgroup.procs'] = lambda x: x

        mem_opts = self._get_options_for('memory')
        for key in mem_opts:
            mem_opts[key] = lambda x: x
        mem_opts['cgroup.procs'] = lambda x: x

        self.__real = CGroupsHierarchyReal()
        self.hierarchy = {
            'cpuset': self.__real.get_info('cpuset', cpu_opts),
            'memory': self.__real.get_info('memory', mem_opts),
        }

    def groups(self, ctrl):
        return self.hierarchy[ctrl].keys()

    def create_group(self, ctrl, group):
        print('mkdir', os.path.join(controller_path(ctrl), group))
        self.hierarchy[ctrl][group] = collections.defaultdict(str)

    def remove_group(self, ctrl, group):
        print('rmdir', os.path.join(controller_path(ctrl), group))
        del self.hierarchy[ctrl][group]

    def get_option(self, ctrl, group, option):
        return self.hierarchy[ctrl][group][option]

    def set_option(self, ctrl, group, option, value):
        print('echo {0} > /sys/fs/cgroup/{1}/{2}/{3}'.format(value.rstrip(), ctrl, group, option))
        self.hierarchy[ctrl][group][option] = str(value)


def get(mock=False):
    """Get a cgroups hierarchy - either real or a mocked one."""
    if mock:
        return CGroupsHierarchyMock()
    return CGroupsHierarchyReal()
