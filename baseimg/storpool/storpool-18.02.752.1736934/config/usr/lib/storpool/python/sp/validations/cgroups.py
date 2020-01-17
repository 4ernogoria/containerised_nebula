"""Provides machine configuration validating checks."""

from __future__ import division

import itertools


from sp import installed
from sp import service as svc
from sp.process import sppidutil
from sp.cgroups import filters
from sp.validations.check import Check as CGCheck
from sp.util import misc as utils
from sp.util.file import parsers


def check_procs(ctrl_name, ctrl_info):
    """Problem reporting function for unknown processes in the storpool cgroups."""
    errors = []
    warnings = []

    def check_sp_cgroup(grp):
        """Check a single cgroup and add errors and warnings for it."""
        pids = ctrl_info[grp]['cgroup.procs']
        for pid, status in sppidutil.recognise(pids).items():
            if status == 'unknown':
                errors.append('{0} pid {1} found in {2}:{3}'
                              .format(status, pid, ctrl_name, grp))
            if status in ('stat', 'controller'):
                warnings.append('{0} pid {1} found in {2}:{3}'
                                .format(status, pid, ctrl_name, grp))
    map(check_sp_cgroup, filter(filters.is_sp_cgroup, ctrl_info))
    return errors, warnings


def group_exists(ctrl_name, ctrl_info, group):
    """Problem reporting function for group existence."""
    if group not in ctrl_info:
        return ['{0}:{1} does not exist'.format(ctrl_name, group)], []
    return [], []


def sp_cpu_exclusive_on(cpuset_info):
    """Problem reporting function for the cpu_exclusive flag of the storpool cpuset."""
    if cpuset_info['storpool.slice']['cpuset.cpu_exclusive'] != 1:
        return ['cpuset:storpool.slice cpu_exclusive is not 1'], []
    return [], []


def groups_nonempty_cpus_mems(cpuset_info):
    """Problem reporting function for non-empty cpuset.{cpus,mems}."""
    errors = []
    for grp in cpuset_info:
        if not cpuset_info[grp]['cpuset.cpus']:
            errors.append('{0} has empty cpuset'.format(grp))
        if not cpuset_info[grp]['cpuset.mems']:
            errors.append('{0} has empty mems'.format(grp))
    return errors, []


def cpusets_split_root(cpuset_info):
    """Problem reporting function for the split of the cpus between the main cgroups."""
    errors = []
    warnings = []
    root_children = filter(filters.is_direct_root_child, cpuset_info)
    for first_child, second_child in itertools.combinations(root_children, 2):
        first_cpuset = set(cpuset_info[first_child]['cpuset.cpus'])
        second_cpuset = set(cpuset_info[second_child]['cpuset.cpus'])
        if first_cpuset != second_cpuset and first_cpuset & second_cpuset:
            errors.append('{0} and {1} cpusets intersect'.format(first_child, second_child))
    children_cpus = set.union(*[set(cpuset_info[child]['cpuset.cpus']) for child in root_children])
    root_cg_cpus = set(cpuset_info['.']['cpuset.cpus'])
    if children_cpus != root_cg_cpus:
        warnings.append('root cgroup cpuset is {0}, while the used cpus are {1}'
                        .format(parsers.list_to_sranges(list(root_cg_cpus)),
                                parsers.list_to_sranges(list(children_cpus))))
    return errors, warnings


def sane_cpusets(cpuset_info):
    """Problem reporting function for cpuset inconsistencies."""
    errors = []
    sp_cg_cpus = cpuset_info['storpool.slice']['cpuset.cpus']
    for grp in filter(filters.is_not_sp_cgroup, cpuset_info):
        ancestor = grp.split('/')[0]
        if set(cpuset_info[grp]['cpuset.cpus']) != set(cpuset_info[ancestor]['cpuset.cpus']):
            errors.append('{0} has different cpuset from {1}'.format(grp, ancestor))
        if grp != '.' and set(cpuset_info[grp]['cpuset.cpus']) & set(sp_cg_cpus):
            errors.append('{0} cpuset intersects with storpool.slice cpuset'.format(grp))
    return errors, []


def sp_subslices_cpusets(cpuset_info):
    """Problem reporting function for storpool groups' cpusets."""
    errors = []
    for grp in filter(filters.is_sp_subgroup, cpuset_info):
        service = grp.split('/')[1]
        if service not in ['rdma', 'server', 'block', 'iscsi', 'mgmt', 'bridge',
                           'beacon'] + svc.strip_prefix(installed.EXTRA_SERVERS):
            errors.append('unknown cpuset:storpool.slice/{0}'.format(service))
        if len(cpuset_info[grp]['cpuset.cpus']) > 1:
            errors.append('{0} subslice has more than 1 cpu'.format(grp))
    return errors, []


def get_cpuset_check(cpuset_info):
    """Returns a base check for the cgroups' cpusets configurations."""
    checks = {}
    checks['root_exists'] = CGCheck([], group_exists, 'cpuset', cpuset_info, '.')
    root_exists = checks['root_exists']
    checks['sys_exists'] = CGCheck([root_exists], group_exists, 'cpuset',
                                   cpuset_info, 'system.slice')
    sys_exists = checks['sys_exists']
    checks['sp_exists'] = CGCheck([root_exists], group_exists, 'cpuset',
                                  cpuset_info, 'storpool.slice')
    sp_exists = checks['sp_exists']
    checks['sp_cpu_exclusive'] = CGCheck([sp_exists], sp_cpu_exclusive_on, cpuset_info)
    checks['cpus_mems'] = CGCheck([], groups_nonempty_cpus_mems, cpuset_info)
    checks['split_root_cpus'] = CGCheck([sys_exists, sp_exists], cpusets_split_root, cpuset_info)
    split_root_cpus = checks['split_root_cpus']
    checks['cpusets_sanity'] = CGCheck([split_root_cpus], sane_cpusets, cpuset_info)
    checks['sp_subslices'] = CGCheck([sp_exists], sp_subslices_cpusets, cpuset_info)
    checks['procs'] = CGCheck([], check_procs, 'cpuset', cpuset_info)
    return CGCheck(checks.values(), lambda: ([], []))


def sp_subslices_memory(memory_info):
    """Problem reporting function for unknown storpool memory subslices."""
    errors = []
    for grp in filter(filters.is_sp_subgroup, memory_info):
        subgrp = grp.split('/')[1]
        if subgrp not in ('alloc', 'common'):
            errors.append('unknown sublsice: memory:{0}'.format(grp))
    return errors, []


def sane_memory_attributes(memory_info):
    """Problem reporting function for valid cgroups memory attributes."""
    errors = []
    warnings = []
    for grp in memory_info:
        mem_lim_mb = memory_info[grp]['memory.limit_in_bytes'] // 1024**2
        memsw_limit_mb = memory_info[grp]['memory.memsw.limit_in_bytes'] // 1024**2
        if mem_lim_mb != memsw_limit_mb:
            errors.append('{0}/memory.limit and memsw.limit differ'.format(grp))
        if memory_info[grp]['memory.use_hierarchy'] == 0:
            arr = warnings if grp == '.' else errors
            arr.append('{0}/memory.use_hierarchy is 0'.format(grp))
        if filters.is_sp_cgroup(grp) or grp in ('system.slice', 'user.slice',
                                                'machine.slice', 'mgmt.slice'):
            if memory_info[grp]['memory.move_charge_at_immigrate'] == 0:
                errors.append('{0}/memory.move_charge_at_immigrate is 0'.format(grp))
        if filters.is_sp_cgroup(grp) and memory_info[grp]['memory.swappiness'] != 0:
            add_to = warnings if grp == 'mgmt.slice' else errors
            add_to.append('{0}/memory.swappiness is not 0'.format(grp))
    return errors, warnings


def get_memory_check(memory_info):
    """Returns a base check for the cgroups' memory configuration."""
    checks = {}
    checks['root_exists'] = CGCheck([], group_exists, 'memory', memory_info, '.')
    root_exists = checks['root_exists']
    checks['sys_exists'] = CGCheck([root_exists], group_exists, 'memory',
                                   memory_info, 'system.slice')
    sys_exists = checks['sys_exists']
    checks['sp_exists'] = CGCheck([root_exists], group_exists, 'memory',
                                  memory_info, 'storpool.slice')
    sp_exists = checks['sp_exists']
    checks['sp_subslices'] = CGCheck([sp_exists], sp_subslices_memory, memory_info)
    checks['sane_attributes'] = CGCheck([sp_exists, sys_exists],
                                        sane_memory_attributes, memory_info)
    checks['procs'] = CGCheck([], check_procs, 'memory', memory_info)
    return CGCheck(checks.values(), lambda: ([], []))


def match_configs(cpuset_info, memory_info):
    """Problem reporting function for missing cpuset or memory slices."""
    errors = []
    for slc in ('user.slice', 'machine.slice'):
        if slc in cpuset_info and slc not in memory_info:
            errors.append('missing memory:{0} subslice'.format(slc))
        if slc in memory_info and slc not in cpuset_info:
            errors.append('missing cpuset:{0} subslice'.format(slc))
    return errors, []


def get_matching_check(cpuset_info, memory_info):
    """Returns a base check for both memory and cpuset configurations."""
    cpuset_check = get_cpuset_check(cpuset_info)
    memory_check = get_memory_check(memory_info)
    return CGCheck([cpuset_check, memory_check], match_configs, cpuset_info, memory_info)


def bad_cgroup_processes():
    """Problem reporting function for storpool processes in wrong cgroups."""
    errors = []
    config = sppidutil.sp_cg_config()
    for pid, service, cpuset, memory in sppidutil.sp_pids_info():
        if service not in config:
            errors.append('no cgroups configuration found for {0}'.format(service))
            continue
        if not cpuset.startswith(config[service]['cpuset']):
            errors.append('{0}({1}) is not in the right cpuset group'.format(pid, service))
        if not memory.startswith(config[service]['memory']):
            errors.append('{0}({1}) is not in the right memory group'.format(pid, service))
    return errors, []


def bad_cgroup_processes_check():
    """Returns a check for wrong cgroups of storpool processes."""
    return CGCheck([], bad_cgroup_processes)


def check_sum_limits(memory_info):
    """Problem reporting function for problems concerning
    the memory left for the kernel.
    """
    slices = ['mgmt.slice', 'storpool.slice', 'user.slice', 'system.slice', 'machine.slice']
    slices = [slc for slc in slices if slc in memory_info]
    limits_mb_sum = sum(memory_info[slc]['memory.limit_in_bytes'] / 1024**2 for slc in slices)
    total_mem_mb = utils.get_memtotal_kb() / 1024
    kernel_mem_mb = max(0, total_mem_mb - limits_mb_sum)
    errors = []
    warnings = []
    if limits_mb_sum >= total_mem_mb:
        errors.append('sum of {0} limits is {1}MB, while total memory is {2}MB'
                      .format(', '.join(slices), limits_mb_sum, total_mem_mb))
    if kernel_mem_mb < 1024:
        warnings.append('memory left for kernel is {0}MB'.format(kernel_mem_mb))
    return errors, warnings


def enough_free_memory(memory_info, slc_name):
    """Problem reporting function for current memory usage."""
    if slc_name not in memory_info:
        return [], []
    crr_limit_mb = memory_info[slc_name]['memory.limit_in_bytes'] // 1024**2
    crr_usage_mb = memory_info[slc_name]['memory.usage_in_bytes'] // 1024**2
    margin = crr_usage_mb / 5  # 20%
    if crr_usage_mb + margin > crr_limit_mb:
        return [], ['memory:{0} has more than 80% usage'.format(slc_name)]
    return [], []


def get_advanced_memory_check(memory_info):
    """Returns an advanced memory check for the memory cgroups."""
    memory_check = get_memory_check(memory_info)
    checks = {}
    checks['sum_limits'] = CGCheck([memory_check], check_sum_limits, memory_info)
    checks['root_usage'] = CGCheck([memory_check], enough_free_memory, memory_info, '.')
    checks['user_usage'] = CGCheck([memory_check], enough_free_memory, memory_info, 'user.slice')
    checks['sys_usage'] = CGCheck([memory_check], enough_free_memory, memory_info, 'system.slice')
    checks['mac_usage'] = CGCheck([memory_check], enough_free_memory, memory_info, 'machine.slice')
    checks['sp_usage'] = CGCheck([memory_check], enough_free_memory, memory_info, 'storpool.slice')
    return CGCheck(checks.values(), lambda: ([], []))
