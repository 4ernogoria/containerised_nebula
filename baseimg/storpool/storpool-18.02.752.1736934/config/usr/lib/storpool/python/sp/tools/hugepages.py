#!/usr/bin/python

from __future__ import print_function

import argparse
import collections
import errno
import logging
import logging.handlers
import mmap
import os
import subprocess
import sys
import tempfile

from storpool import spconfig

from sp import installed
from sp import spmemory
from sp import messages as m
from sp import service as svc
from sp.process import pidutil
from sp.util import decorators as spd
from sp.util.file import writers


NVME_HP_CONF_VAR_PHYSMEM = 'SP_NVME_HUGEPAGES_PHYSMEM'
NVME_HP_CONF_VAR_DISKS = 'SP_NVME_HUGEPAGES_DISKS'
CFG_FILE = '/etc/storpool.conf.d/hugepages.conf'


@spd.static_vars(logger=None)
def get_logger():
    if get_logger.logger is None:
        logger = logging.getLogger(sys.argv[0])
        logger.setLevel(logging.INFO)
        dhandler = logging.handlers.SysLogHandler(address='/dev/log')
        formatter = logging.Formatter('%(name)s[%(process)d]: %(message)s')
        dhandler.setFormatter(formatter)
        logger.addHandler(dhandler)
        get_logger.logger = logger
    return get_logger.logger


def get_args_parser():
    parser = argparse.ArgumentParser(description='StorPool hugepages utility.')

    parser.add_argument('-e', '--errexit', action='store_true', default=False,
                        help='exit with a non-zero error code on any problems')
    parser.add_argument('-N', '--noop', action='store_true', default=False,
                        help='no operation')
    parser.add_argument('-s', '--skip-checks', action='store_true', default=False,
                        help='Skip checking for release version (used for upgrades)')
    parser.add_argument('-R', '--reserve-only', action='store_true', default=False,
                        help='use the value already specified in the StorPool configuration'
                             'instead of calculating it')
    parser.add_argument('-S', '--services', type=str,
                        help='specify the running services on the machine')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='verbose level')
    return parser


def get_args():
    parser = get_args_parser()
    args = parser.parse_args()

    if args.services:
        args.services = svc.strip_prefix([
            service for service in args.services.replace(',', ' ').split()
        ])
        bad = [service for service in args.services if service not in spmemory.HUGEPAGE_SERVICES]
        if bad:
            parser.error('invalid services: {0}'.format(bad))
    else:
        args.services = svc.strip_prefix(installed.services())

    return args


def get_sp_numa():
    sp_numa = spmemory.sp_numa(default=0)
    if not spmemory.check_hugepage_sz(numa=sp_numa):
        msg = 'No {sz}kB hugepages on numa {n}'.format(sz=spmemory.HUGEPAGES_SZ_KB, n=sp_numa)
        get_logger().critical(msg)
        m.exit_msg(msg)
    return sp_numa


FAILED_TO_RESERVE_MSG_TMPL = 'Failed to reserve the required {nr} pages - '\
                             'could not modify the nr_hugepages file.'


def ensure_hugetlb_mount(path, args):
    """ Make sure that 2MB hugepages are mounted at the specified path. """
    if not os.path.isdir(path):
        if args.noop:
            m.msg('Would create {path}'.format(path=path))
        else:
            os.makedirs(path, 0o750)

    found = False
    with open('/proc/mounts', mode='r') as mounts:
        for line in mounts.readlines():
            fields = line.split()
            if len(fields) < 2 or fields[1] != path:
                continue
            if len(fields) < 4:
                sys.exit('Unexpected line in /proc/mounts: {line}'
                         .format(line=line))
            if fields[2] != 'hugetlbfs':
                sys.exit('Unexpected filesystem type for {path} in '
                         '/proc/mounts: {line}'.format(path=path, line=line))
            if 'rw' not in set(fields[3].split(',')):
                sys.exit('Unexpected options (no "rw") for {path} in '
                         '/proc/mounts: {line}'.format(path=path, line=line))
            found = True

    if not found:
        cmd = [
            'mount', '-t', 'hugetlbfs', '-o', 'rw,pagesize=2M',
            'hugetlb2m', path
        ]
        if args.noop:
            m.msg('Would run {cmd}'.format(cmd=' '.join(cmd)))
        else:
            subprocess.check_call(cmd)


def get_current_hp_files(path, args, nvme_hp_needed):
    """ Figure out what files need creating or truncating. """
    all_svc = (set(args.services) & spmemory.HUGEPAGE_SERVICES)
    if 'storpool_nvmed' in installed.services():
        all_svc = all_svc | set(['nvmed', 'nvmed_disks'])

    try:
        res = spmemory.get_services_hp(all_svc, path, nvme_hp_needed)
    except spmemory.ExamineError as err:
        sys.exit(err)

    names = \
        (['beacon'] if 'beacon' in res else []) + \
        (['block'] if 'block' in res else []) + \
        sorted(set(res.keys()) - set(['beacon', 'block']))
    return [res[name] for name in names]


class CreateFileException(Exception):
    def __init__(self, service, action, exc):
        self._service = service
        self._action = action
        self._exc = exc

    def __str__(self):
        return 'Could not {act} the {svc} service hugepages file: {exc}' \
            .format(act=self._action, svc=self._service, exc=self._exc)


def create_hp_file(data, args, hp_needed, hp_more, sp_numa):
    """ Create, extend, and reserve a hugepages file for a service. """
    if data.current_pages is None:
        try:
            fd = os.open(data.path, os.O_RDWR | os.O_CREAT | os.O_EXCL)
        except (OSError, IOError) as exc:
            raise CreateFileException(data.service, 'create', exc)
        current_pages = 0
    else:
        if data.current_pages >= data.expected_pages:
            return 0
        try:
            fd = os.open(data.path, os.O_RDWR)
        except (OSError, IOError) as exc:
            raise CreateFileException(data.service, 'open', exc)
        current_pages = data.current_pages

    if data.expected_pages == 0:
        try:
            os.close(fd)
        except (OSError, IOError) as exc:
            pass
        return 0

    mm = None
    try:
        stat = os.fstat(fd)
        hp_in_mb = spmemory.HUGEPAGES_SZ_B
        if stat.st_size != current_pages * hp_in_mb:
            raise CreateFileException('process', Exception(
                'the file size changed underneath us: expected {exp} bytes, '
                'got {cur} bytes'.format(exp=current_pages * hp_in_mb,
                                         cur=stat.st_size)))

        assert current_pages < data.expected_pages
        new_size = data.expected_pages * hp_in_mb
        try:
            m.msg('- extending to {new_size}'.format(new_size=new_size))
            os.ftruncate(fd, new_size)
        except (IOError, OSError) as exc:
            raise CreateFileException(data.service, 'extend', exc)

        incr = 16
        for attempt in range(16):
            if attempt != 0:
                hp_more += incr
                hp_new = hp_needed + hp_more
                msg = '- reserving {incr} more pages, total {ttl}'.format(
                    incr=incr, ttl=hp_new)
                get_logger().info(msg)
                m.msg(msg)

                if not spmemory.set_nr_hugepages(hp_new, sp_numa):
                    raise CreateFileException(data.service, 'reserve',
                        Exception(FAILED_TO_RESERVE_MSG_TMPL
                                  .format(nr=hp_new)))

            m.msg('- attemping to map {size} bytes'.format(size=new_size))
            try:
                mm = mmap.mmap(fd, new_size)
                break
            except (OSError, IOError, mmap.error) as exc:
                if exc.errno == errno.ENOMEM:
                    continue
                raise
        else:
            raise CreateFileException(data.service, 'map',
                Exception('Could not reserve enough hugepages'))

        total = 0
        m.msg('- touching pages {cur}-{exp}'
              .format(cur=current_pages, exp=data.expected_pages - 1))
        for page_no in range(current_pages, data.expected_pages):
            total += ord(mm[page_no * hp_in_mb])

        m.msg('- done')
    except BaseException as exc:
        if data.current_pages is None:
            m.msg('- something went wrong, trying to remove the file')
            try:
                os.unlink(data.path)
            except (IOError, OSError):
                pass
        else:
            m.msg('- something went wrong, trying to shrink the file back '
                  'down to {current_size}'.format(current_size=stat.st_size))
            try:
                os.ftruncate(fd, stat.st_size)
            except (IOError, OSError):
                pass

        if isinstance(exc, CreateFileException):
            raise
        else:
            raise CreateFileException(data.service, 'handle', exc)
        raise
    finally:
        if mm is not None:
            try:
                mm.close()
            except (IOError, OSError, mmap.error):
                pass
        try:
            os.close(fd)
        except (IOError, OSError):
            pass

    return hp_more


def cgclassify_self(ctrl, group):
    """ Attempt to move to the specified cgroup.

    If this is not done, it is possible that any further actions will
    fail since the kernel may not allow this process to modify
    hugepage reservations for other NUMA nodes. """
    current = pidutil.cgroups(os.getpid()).get(ctrl)
    if current == group:
        return

    m.msg('Trying to migrate from {ctrl} cgroup {cur} to {grp}'
          .format(ctrl=ctrl, cur=repr(current), grp=repr(group)))
    cg = subprocess.Popen(
        [
            'cgclassify', '-g', ctrl + ':' + group,
            '--', str(os.getpid())
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = cg.communicate()
    res = cg.returncode
    if res != 0:
        msg = 'Could not migrate to {ctrl} cgroup "{group}": '\
              'cgclassify exited with code {res}; '\
              'stdout: {out}; stderr: {err}'.\
              format(ctrl=ctrl, group=group, res=res,
                     out=repr(output[0]), err=repr(output[1]))
        get_logger().critical(msg)
        m.exit_msg(msg)


def set_hp(args, nvme_hp_needed, write_conf=True):
    cgclassify_self('cpuset', '/')

    sp_numa = get_sp_numa()

    path = spmemory.sp_hugepages_path()
    ensure_hugetlb_mount(path, args)
    files = get_current_hp_files(path, args, nvme_hp_needed)

    hp_needed = sum(data.expected_pages for data in files)
    hp_current = spmemory.get_nr_hugepages(sp_numa)

    if args.noop:
        m.msg('hugepages: current {current}, want {want}, numa: {numa}'
              .format(current=hp_current, want=hp_needed, numa=sp_numa))
        if hp_needed < hp_current:
            m.msg('- will not decrease')
        elif hp_needed == hp_current:
            m.msg('- will not change')
        m.msg('Services: {0}'.format(set(args.services) & spmemory.HUGEPAGE_SERVICES))
        m.msg('SP nvme devices: {0}'.format(spmemory.sp_nvme_devices()))
        m.msg('SP nvme device partitions: {0}'.format(spmemory.sp_nvme_devices_partitions()))
        m.msg('SP hugepage files:')
        for data in files:
            m.msg('- {path} current {current_pages} expected {expected_pages}'
                  ' - {ok}'
                  .format(path=data.path, current_pages=data.current_pages,
                          expected_pages=data.expected_pages,
                          ok='OK' if data.current_pages >= data.expected_pages
                          else 'to fix'))
    else:
        if hp_needed > hp_current:
            get_logger().info(
                'setting %d (including %d(nvme phys) + %d(nvme disks)) '
                'hugepages on numa %d (currently %d)',
                hp_needed, nvme_hp_needed.phys, nvme_hp_needed.disks,
                sp_numa, hp_current)
            if not spmemory.set_nr_hugepages(hp_needed, sp_numa):
                msg = FAILED_TO_RESERVE_MSG_TMPL.format(nr=hp_needed)
                get_logger().critical(msg)
                m.exit_msg(msg)
        else:
            get_logger().info(
                'already have %d (including %d(nvme phys) + %d(nvme disks)) '
                'hugepages on numa %d (currently %d)',
                hp_needed, nvme_hp_needed.phys, nvme_hp_needed.disks,
                sp_numa, hp_current)
        if write_conf:
            tmpl = '''# StorPool hugepage requirements
# (automatically generated by storpool_hugepages)
#
# 1 if storpool_nvmed runs on this host, 0 otherwise
{var_phys}={hp_phys}

# 6 per NVME partition (or, if not using partitions, 6 per NVME drive)
{var_disks}={hp_disks}
'''
            writers.write_file(CFG_FILE, tmpl.format(
                var_phys=NVME_HP_CONF_VAR_PHYSMEM,
                var_disks=NVME_HP_CONF_VAR_DISKS,
                hp_phys=nvme_hp_needed.phys,
                hp_disks=nvme_hp_needed.disks))

        hp_more = 0
        for data in files:
            m.msg('Handling {path}: current {csz}, expected {esz}'
                  .format(path=data.path, csz=data.current_pages,
                          esz=data.expected_pages))
            try:
                hp_more = create_hp_file(data, args, hp_needed,
                                         hp_more, sp_numa)
            except CreateFileException as exc:
                if data.service in ('beacon', 'block') or args.errexit:
                    msg = str(exc) + '; aborting'
                    get_logger().critical(msg)
                    m.exit_msg(msg)
                else:
                    msg = str(exc) + '; still proceeding'
                    get_logger().warning(msg)
                    m.warn_msg(msg)
                    continue


def main():
    args = get_args()
    m.set_verbose_level(args.verbose)
    if not spmemory.sp_supports_hugepages():
        if args.noop:
            m.msg('Current StorPool does not support hugepages.')
        if not args.skip_checks:
            m.exit_msg('Use -s to skip this check and attempt to reserve anyway.')
        else:
            m.msg('Skip checks selected, proceeding anyway.')

    try:
        cfg = spconfig.SPConfig()
        nvme_last = spmemory.HugePagesNVME(
            phys=int(cfg.get(NVME_HP_CONF_VAR_PHYSMEM, 0)),
            disks=int(cfg.get(NVME_HP_CONF_VAR_DISKS, 0)),
        )
    except Exception:
        if args.reserve_only:
            raise

        m.msg('Could not read the StorPool configuration, '
              'assuming no stored hugepages settings')
        nvme_last = spmemory.HugePagesNVME(
            phys=0,
            disks=0,
        )

    if args.reserve_only:
        set_hp(args, nvme_last, write_conf=False)
    else:
        nvme_detected = spmemory.nvme_hugepages_split()
        nvme_req_phys = 1 if 'storpool_nvmed' in installed.services() else 0
        nvme_safe = spmemory.HugePagesNVME(
            phys=max(nvme_detected.phys, nvme_last.phys, nvme_req_phys),
            disks=max(nvme_detected.disks, nvme_last.disks),
        )
        set_hp(args, nvme_safe, write_conf=True)


if __name__ == '__main__':
    main()
