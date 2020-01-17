#!/usr/bin/python

import json
import multiprocessing.dummy
import sys

from storpool import spapi, sptypes

sys.path.append('/usr/lib/storpool/python')
from sp.util import decorators as spd

DISK_TIMEOUT = 1 * 10 * 1000
CLIENT_TIMEOUT = 1 * 10 * 1000
SYSTEM_TIMEOUT = 1 * 300 * 1000
J = 0

# function call timeout in seconds
GLOBAL_TIMEOUT = 10

def usage():
    '''print usage and exit'''
    print """Usage: {n} [DISK_TIMEOUT=value] [CLIENT_TIMEOUT=value] \
    [GLOBAL_TIMEOUT=value] [SYSTEM_TIMEOUT=value] [J=value]

    Defaults:
    DISK_TIMEOUT, CLIENT_TIMEOUT: 10000 (in ms)
    SYSTEM_TIMEOUT: 60000 (in ms)
    GLOBAL_TIMEOUT: 10 (in sec)
    J: stands for json output, default 0 (off)
    """.format(n=sys.argv[0])

def chkval(arg):
    '''check if the argument's value is int and return,
    print usage and exit if not'''
    try:
        return int(arg)
    except ValueError:
        print '{s} is not int'.format(s=arg)
        exit(1)

if len(sys.argv[1:]) > 0:
    # reading commandline parameters
    if sys.argv[1] == '-h' or sys.argv[1] == '--help' or sys.argv[1] == 'usage':
        usage()
        exit(0)
    else:
        for arg in sys.argv[1:]:
            try:
                (var, val) = arg.split('=', 1)
            except ValueError:
                print 'Argument {a} not a var=value pair'.format(a=arg)
                exit(1)
            if var == 'DISK_TIMEOUT':
                DISK_TIMEOUT = chkval(val)
            elif var == 'CLIENT_TIMEOUT':
                CLIENT_TIMEOUT = chkval(val)
            elif var == 'GLOBAL_TIMEOUT':
                GLOBAL_TIMEOUT = chkval(val)
            elif var == 'SYSTEM_TIMEOUT':
                SYSTEM_TIMEOUT = chkval(val)
            elif var == 'J':
                J = chkval(val)
            else:
                print 'Unknown variable {var}'.format(var=var)
                exit(1)

def logrequest(node, rqmsec, reqid, reqop, reqvol):
    print >> sys.stderr, "{n:>10} {rm:>10} {ri:>40} {ro:>11} {rv}".format(n=node, \
    rm=rqmsec, ri=reqid, ro=reqop, rv=reqvol)

def checkactiverequestsstar(allargs):
    return checkactiverequests(*allargs)

def checkactiverequests(node, arob, timeout, systimeout):
    '''
    node: int ID of disk/client
    arob: ActiveRequestDesc object
    to: int timeout (for disk or client requests)
    st: int timeout (fod system requests)
    returns tuple (node, result) if any, else None
    '''
    minr = min(timeout, systimeout)
    allreqs = filter(lambda r: r.msecActive >= minr, arob['requests'])
    usrreqs = filter(lambda r: not r.volume.startswith('#'), allreqs)
    sysreqs = filter(lambda r: r.volume.startswith('#'), allreqs)
    res = filter(lambda r: r.msecActive >= timeout and r.op in ('read', 'write'), usrreqs) \
    + filter(lambda r: r.msecActive >= systimeout, sysreqs)
    if len(res) > 0:
        return node, res
    else:
        return None

def getactiverequests(i):
    '''
    value: single element from the output of either:
    - api.diskActiveRequests.values()
    - api.clientActiveRequests.clients.values()
    disks: list object
    returns None, invokes checkactiverequestsstar
    '''
    if isinstance(i, sptypes.UpDiskSummary):
        return checkactiverequestsstar(
            [
                i.id,
                api.diskActiveRequests(i.id).toJson(),
                DISK_TIMEOUT,
                SYSTEM_TIMEOUT
            ]
        )
    elif isinstance(i, sptypes.Client):
        if i.status == 'running':
            return checkactiverequestsstar(
                [
                    i.id,
                    api.clientActiveRequests(i.id).toJson(),
                    CLIENT_TIMEOUT,
                    SYSTEM_TIMEOUT
                ]
            )
    elif isinstance(i, sptypes.DownDiskSummary):
        return None
    else:
        print >>sys.stderr, '"{t}" is not handled'.format(t=type(i))

def show(reqs):
    for request in reqs:
        rid = request[0]
        vals = request[1]
        if rid == 0:
            logrequest(*vals)
        else:
            for req in vals:
                # {
                #     'prevState': 'CL_READ_START',
                #     'requestIdx': 740,
                #     'drOp': 'DATA_DISK_OP_NONE',
                #     'volume': 's11-ntfs-hdd-r3-single-shrinkOk-1-148G-tmp',
                #     'state': 'CL_READ_XFER',
                #     'requestId': '9226469785490340236:208291482856663335',
                #     'address': 79467380736L,
                #     'size': 4096,
                #     'msecActive': 0,
                #      'op': 'read'
                #  }
                logrequest(rid, req.msecActive, req.requestId, req.op, req.volume)

@spd.timeout(GLOBAL_TIMEOUT)
def main():
    pool = multiprocessing.dummy.Pool(4)
    dreqs = []
    creqs = []
    dresult = filter(
        lambda x: x is not None,
        pool.map(getactiverequests, api.disksList().values())
    )
    dreqs.extend(dresult)
    cresult = filter(
        lambda c: c is not None,
        pool.map(getactiverequests, api.servicesList().clients.values())
    )
    creqs.extend(cresult)
    if J:
        # unpack requests only and move to dict
        dumpdict = {'disks':{}, 'clients':{}}
        for tup in dreqs:
            # each t is (id, [request1, request2, ...])
            diskid = tup[0]
            dumpdict['disks'][diskid] = [l.toJson() for l in tup[1]]
        for tup in creqs:
            # each t is (id, [request1, request2, ...])
            cid = tup[0]
            dumpdict['clients'][cid] = [l.toJson() for l in tup[1]]
        json.dump({'data': dumpdict}, sys.stdout, indent=1)
        print
    else:
        if any(dreqs):
            dreqs.insert(0, (0, ["disk ID", "msec.", "request ID", "op", "volume"]))
            show(dreqs)
        if any(creqs):
            creqs.insert(0, (0, ["client ID", "msec.", "request ID", "op", "volume"]))
            show(creqs)
    pool.terminate()

if __name__ == '__main__':
    try:
        api = spapi.Api.fromConfig()
        main()
        exit(0)
    except spd.TimeoutError as err:
        msg = 'Timed out after {s} second(s)'.format(s=GLOBAL_TIMEOUT)
        if J:
            errmsg = {'error': {'name': type(err).__name__, 'descr': msg}}
            print '{j}\n'.format(j=json.dumps(errmsg))
        else:
            print >>sys.stderr, msg
        exit(1)
    except Exception as err:
        if J:
            errmsg = {'error': {'name': type(err).__name__, 'descr': str(err)}}
            print '{j}\n'.format(j=json.dumps(errmsg))
        else:
            print >> sys.stdout, err
