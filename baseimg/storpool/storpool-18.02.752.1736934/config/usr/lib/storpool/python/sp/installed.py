""" Provides information for installed StorPool binaries, modules and services. """

import glob
import os


import sp.service


MAX_SERVERS = 16


EXTRA_SERVERS = ['storpool_server_{n}'.format(n=i) for i in range(1, MAX_SERVERS)]


SERVICES = ['storpool_beacon', 'storpool_block', 'storpool_bridge',
            'storpool_controller', 'storpool_iscsi', 'storpool_kdump',
            'storpool_mgmt', 'storpool_nvmed', 'storpool_reaffirm',
            'storpool_stat', 'storpool_server'] + EXTRA_SERVERS


SERVICE_PATH_TMPL = '/usr/sbin/{s}.bin'
SERVER_LINK_TMPL = '/usr/sbin/{s}'


def enabled_services():
    """Returns a list of the enabled StorPool services."""
    return [service for service, status in sp.service.check_services(SERVICES)
            if status == 'enabled']


def services():
    """Returns a list of the installed StorPool services."""
    installed_services = set(glob.glob(SERVICE_PATH_TMPL.format(s='storpool_*')))
    if SERVICE_PATH_TMPL.format(s='storpool_server') in installed_services:
        extra_s = [svc for svc in EXTRA_SERVERS
                   if os.path.islink(SERVER_LINK_TMPL.format(s=svc))]
        installed_services.update(SERVICE_PATH_TMPL.format(s=server)
                                  for server in extra_s)
    return [service for service in SERVICES
            if SERVICE_PATH_TMPL.format(s=service) in installed_services]
