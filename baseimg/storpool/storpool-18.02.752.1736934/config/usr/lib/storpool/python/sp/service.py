"""
Check whether the specified system services are installed and enabled.
"""

import os


from sp.util import misc as utils
from sp.util import decorators as spd
from sp.util.backports import subprocess


SP_PREFIX = 'storpool_'
SP_PREFIX_LEN = len(SP_PREFIX)


@spd.static_vars(runlevel=None)
def check_service_sysv(svc):
    """ Check whether a SysV service is installed and enabled. """
    if check_service_sysv.runlevel is None:
        check_service_sysv.runlevel = utils.get_runlevel()

    if not os.path.isfile('/etc/init.d/' + svc):
        return 'not-installed'

    dirname = '/etc/rc{run}.d'.format(run=check_service_sysv.runlevel)
    for fname in os.listdir(dirname):
        if fname.startswith('S') and fname[3:] == svc:
            return 'enabled'

    return 'disabled'


@spd.static_vars(lines=None)
def check_service_systemd(svc):
    """ Check whether a systemd service is installed and enabled. """
    if check_service_systemd.lines is None:
        raw = subprocess.check_output(['systemctl', 'list-unit-files',
                                       '--no-pager', '--no-legend'])
        check_service_systemd.lines = raw.decode('UTF-8').rstrip().split('\n')

    svc_name = svc + '.service'
    for line in check_service_systemd.lines:
        fields = line.split()
        if not fields or fields[0] != svc_name:
            continue
        if len(fields) == 1:
            # Eh?!
            return 'disabled'

        # Let's hope we don't have to check for static services...
        return 'enabled' if fields[1] == 'enabled' else 'disabled'

    return check_service_sysv(svc)


def check_services(names):
    """ Return a list of (service-name, status) tuples. """
    check = check_service_systemd if utils.is_systemd() else check_service_sysv
    return [(svc, check(svc)) for svc in names]


def add_prefix(data):
    """ Make sure the "storpool_" prefix is there for service names. """
    def add_single(name):
        """ Make sure the "storpool_" prefix is there for a single name. """
        return name if name.startswith(SP_PREFIX) else SP_PREFIX + name

    if isinstance(data, str):
        return add_single(data)

    return [add_single(name) for name in data]


def strip_prefix(data):
    def strip_single(name):
        """ Make sure there is no "storpool_" prefix for a single name. """
        return name[SP_PREFIX_LEN:] if name.startswith(SP_PREFIX) else name

    if isinstance(data, str):
        return strip_single(data)

    return [strip_single(name) for name in data]
