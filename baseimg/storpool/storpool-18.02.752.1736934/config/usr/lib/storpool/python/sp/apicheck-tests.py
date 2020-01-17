#!/usr/bin/python
#
#-
# Copyright (c) 2018  StorPool.
# All rights reserved.
#

import socket
import time
import unittest

if __name__ == '__main__':
    import sys

    sys.path.insert(0, 'lib/storpool')
    sys.path.insert(0, 'scripts/usr/lib/storpool/python')

from storpool import spapi, spconfig

from sp.util import decorators, misc

def apichecks(cfg=None, api=None, ctrlport=None, timeoutseconds=10):
    '''
    cfg: spconfig.SPConfig() object
    api: api.fromConfig() object

    returns dict[('SP_API_HTTP_HOST', 'SP_CONTROLLER_PORT')] = bool
            dict[('SP_API_HTTP_HOST', 'SP_API_HTTP_PORT')] = bool
    '''
    @decorators.timeout(seconds=timeoutseconds)
    def reqapi(api):
        '''tests api.servicesList, raises TimeoutError in case it does not reply
        in reasonable time'''
        return api.servicesList()

    if not cfg:
        cfg = spconfig.SPConfig()
    res = {}
    res['ctrl_sock'] = {}
    if 'SP_API_HTTP_HOST' in cfg:
        # SP_API_HTTP_HOST configured
        # check the reachability of the controller port 47567
        if not ctrlport:
            ctrlport = 47567
        tupc = (cfg['SP_API_HTTP_HOST'], ctrlport)
        res['ctrl_sock']['socket'] = tupc
        res['ctrl_sock']['reply'] = misc.scheck(tupc)
    res['api_sock'] = {}
    if 'SP_AUTH_TOKEN' in cfg and 'SP_API_HTTP_PORT' in cfg:
        # test a TCP connection to API host:port
        tupa = (cfg['SP_API_HTTP_HOST'], int(cfg['SP_API_HTTP_PORT']))
        res['api_sock']['socket'] = tupa
        res['api_sock']['reply'] = misc.scheck(tupa)
        if res['api_sock']['reply'] and 'SP_AUTH_TOKEN' in cfg:
            # attempt to run a service list
            if not api:
                api = spapi.Api.fromConfig()
            res['api_reply'] = {}
            try:
                repl = reqapi(api)
                if repl and 'mgmt' in repl.toJson():
                    res['api_reply']['reply'] = True
                else:
                    res['api_reply']['reply'] = False
                    res['api_reply']['error'] = repl
            except (decorators.TimeoutError, spapi.ApiError) as err:
                res['api_reply']['reply'] = False
                res['api_reply']['error'] = str(err)
    return res

class Api(object):
    def __init__(self, arg=None, timeout=None, raised=False):
        self.arg = arg
        self.timeout = timeout
        self.raised = raised
    def servicesList(self):
        '''false Api, return whatever was configured for this instance at
        __init__ (or later)'''
        if self.timeout:
            time.sleep(self.timeout)
        return self.arg
    def toJson(self):
        if self.timeout:
            time.sleep(self.timeout)
        if self.raised:
            raise spapi.ApiError(2, {'error': {'descr': 'invalid request'}})
        return self.arg

def listensocket(port):
    host = ''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(1)
    return sock

def checktestports(lports):
    for port in lports:
        if misc.scheck(('127.0.0.1', port)):
            print 'Test port {p} being used, please retry'.format(p=port)

class ApiChecks(unittest.TestCase):

    def test_no_access(self):
        # no access to SP_API_HTTP_HOST (localhost), ctrl unreachable, no SP_AUTH_TOKEN
        cfg = {'SP_API_HTTP_HOST': '127.0.0.1', 'SP_API_HTTP_PORT': 50001}
        expected = {'api_sock': {}, 'ctrl_sock': {'reply': False, 'socket': ('127.0.0.1', 50002)}}
        self.assertEqual(apichecks(cfg=cfg, ctrlport=50002), expected)

    def test_access(self):
        # access to SP_API_HTTP_HOST, ctrl port unreachable, no SP_AUTH_TOKEN
        checktestports([50001, 50002])
        cfg = {'SP_API_HTTP_HOST': '127.0.0.1', 'SP_API_HTTP_PORT': 50001}
        apisock = listensocket(cfg['SP_API_HTTP_PORT'])
        result = {'api_sock': {}, 'ctrl_sock': {'reply': False, 'socket': ('127.0.0.1', 50002)}}
        self.assertEqual(apichecks(cfg=cfg, ctrlport=50002), result)
        apisock.close()

    def test_access_ctrl(self):
        # access to SP_API_HTTP_HOST, ctrl port reachable, no SP_AUTH_TOKEN
        checktestports([50001, 50002])
        cfg = {'SP_API_HTTP_HOST': '127.0.0.1', 'SP_API_HTTP_PORT': 50001}
        apisock = listensocket(cfg['SP_API_HTTP_PORT'])
        ctrlsock = listensocket(50002)
        result = {'api_sock': {}, 'ctrl_sock': {'reply': True, 'socket': ('127.0.0.1', 50002)}}
        self.assertEqual(apichecks(cfg=cfg, ctrlport=50002), result)
        apisock.close()
        ctrlsock.close()

    def test_access_auth(self):
        # access to SP_API_HTTP_HOST, ctrl port unreachable, with SP_AUTH_TOKEN
        checktestports([50001])
        cfg = {'SP_API_HTTP_HOST': '127.0.0.1', 'SP_API_HTTP_PORT': 50001, 'SP_AUTH_TOKEN': 1}
        apisock = listensocket(cfg['SP_API_HTTP_PORT'])
        api = Api(Api({'mgmt':{}}))
        result = {'api_sock': {'reply': True, 'socket': ('127.0.0.1', 50001)}, \
            'api_reply': {'reply': True}, 'ctrl_sock': {'reply': False, \
            'socket': ('127.0.0.1', 50002)}}
        self.assertEqual(apichecks(cfg=cfg, api=api, ctrlport=50002), result)
        apisock.close()

    def test_access_auth_timeout(self):
        # access to SP_API_HTTP_HOST, ctrl port unreachable, SP_AUTH_TOKEN, timeouts
        checktestports([50001])
        cfg = {'SP_API_HTTP_HOST': '127.0.0.1', 'SP_API_HTTP_PORT': 50001, 'SP_AUTH_TOKEN': 1}
        apisock = listensocket(cfg['SP_API_HTTP_PORT'])
        api = Api({}, timeout=2)
        result = {'api_sock': {'reply': True, 'socket': ('127.0.0.1', 50001)}, \
            'api_reply': {'reply': False, 'error': 'Timer expired'}, \
            'ctrl_sock': {'reply': False, 'socket': ('127.0.0.1', 50002)}}
        self.assertEqual(apichecks(cfg=cfg, api=api, ctrlport=50002, \
            timeoutseconds=1), result)
        apisock.close()

    def test_access_auth_error(self):
        # access to SP_API_HTTP_HOST, ctrl port unreachable, SP_AUTH_TOKEN, invalid request
        checktestports([50001])
        cfg = {'SP_API_HTTP_HOST': '127.0.0.1', 'SP_API_HTTP_PORT': 50001, 'SP_AUTH_TOKEN': 1}
        apisock = listensocket(cfg['SP_API_HTTP_PORT'])
        # raises an ApiError similar to what would be returned with wrong auth token
        api = Api(Api({'mgmt': {}}, raised=True))
        result = {'api_sock': {'reply': True, 'socket': ('127.0.0.1', 50001)}, \
            'api_reply': {'reply': False, 'error': '<Missing error name>: invalid request'}, \
            'ctrl_sock': {'reply': False, 'socket': ('127.0.0.1', 50002)}}
        self.assertEqual(apichecks(cfg=cfg, api=api, ctrlport=50002), result)
        apisock.close()

if __name__ == '__main__':
    unittest.main()
