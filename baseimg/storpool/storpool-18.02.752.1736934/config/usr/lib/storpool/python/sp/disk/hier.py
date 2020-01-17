#!/usr/bin/env python
from __future__ import print_function
from distutils.spawn import find_executable

from sp.util.backports import subprocess

try:
    from decorator import decorator
except ImportError:
    def decorator(caller):
        def decor(f):
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                return caller(f, *args, **kwargs)
            return wrapper
        return decor

import glob
import functools
import json
import logging
import logging.handlers
import os
import re
import sys
import stat
import string
import syslog
import tempfile
import time

logger = logging.getLogger(sys.argv[0])
logger.setLevel(logging.INFO)
handler = logging.handlers.SysLogHandler()
logger.addHandler(handler)
if sys.stdout.isatty():
    # initialises output to stdout as well
    clogger = logging.StreamHandler(sys.stdout)
    clogger.setLevel(logging.INFO)
    logger.addHandler(clogger)

def retry(exceptions=Exception, tries=-1, delay=0, backoff=1, debug=False):
    """Returns a retry decorator.
    exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    tries: the maximum number of attempts. default: -1 (infinite).
    delay: initial delay between attempts. default: 0.
    backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    returns a retry decorator.
    """

    def __retry_internal(f, exceptions=Exception, tries=-1, delay=0, backoff=1, debug=False):
        """
        Executes a function and retries it if it failed.
        f: the function to execute.
        exceptions: an exception or a tuple of exceptions to catch. default: Exception.
        tries: the maximum number of attempts. default: -1 (infinite).
        delay: initial delay between attempts. default: 0.
        max_delay: the maximum value of delay. default: None (no limit).
        backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
        returns the result of the f function.
        """
        _tries, _delay = tries, delay
        while _tries:
            try:
                return f()
            except exceptions as e:
                _tries -= 1
                if not _tries:
                    raise
                if debug > 1:
                    # only for -dd or more verbose
                    logger.info('{err}, retrying in {s} seconds...'.format(err = e, s = _delay))
                time.sleep(_delay)
                _delay *= backoff

    @decorator
    def retry_decorator(f, *fargs, **fkwargs):
        args = fargs if fargs else list()
        kwargs = fkwargs if fkwargs else dict()
        return __retry_internal(functools.partial(f, *args, **kwargs), exceptions, tries, delay, backoff, debug)
    return retry_decorator

# MCommon (common methods)
# |\_Controller
# | \
# |  \_PhysDisk
# |            \
# BDCommon_     \              BlockDevice
#        | \_____VirtualDev___/           \__StorPoolDisk_
#        |                                |               |
#        \________________________________\_Partition____/

class RetryException(BaseException):
    def __init__(arg):
        pass

class MCommon(object):
    """
    Master Common class for methods inheritance
    self.simulate - whether to execute or just print commands
    self.debug - verbose output

    methods:
    self.die - exit with an error and print an error message
    self.run:
     - if self.simulate is True (default) print/log command to stdout
     - if self.simulate is False, execute the command
    self.say, self.saycrit - print/log messages
    self.get_json - when prompting for harmless json output
    """

    def __init__(self, simulate, debug = False):
        super(MCommon, self).__init__()
        self.simulate = simulate
        self.debug = debug

    def die(self, msg):
        '''msg: str message to print/log
        exits in case of failure'''
        logger.critical(msg)
        exit(1)

    def dumpdebug(self, cmd, output):
        '''
        dumps the output into a file in /tmp with
        /tmp/pid/tstamp-cmd_arg1_arg2...
        '''
        # directory to save the outputs in
        pref = '-'.join([str(os.path.basename(__file__)), str(os.getpid())])
        path = os.path.join('/tmp', pref)
        if not os.path.isdir(path):
            os.mkdir(path)
        tfile = os.path.join(path, '-'.join([str(int(time.time()*1000)), str(os.path.basename(cmd.split()[0]))]))
        with open(tfile, 'w') as tf:
            tf.write(cmd + '\n\n' + output)

    def say(self, msg):
        logger.info(msg)

    def saycrit(self, msg):
        logger.critical(msg)

    def get_json(self, cmd):
        return json.loads(self.run(cmd, simulate = False)) # safe command

    def run(self, cmd, simulate = True, fail = False):
        try:
            if simulate:
                self.say('# Simulation - would execute:\n{c}'.format(c = cmd))
                return
            out = subprocess.check_output(cmd.split(), stderr = None)
            if self.debug > 1:
                self.say('Command execution succeeded:\n{c}\n{o}'.format(c = cmd, o = out))
            if self.debug:
                self.dumpdebug(cmd, out)
            return out
        except subprocess.CalledProcessError as e:
            msg = 'Command execution failed:\n{c}'.format(c = cmd)
            if fail:
                if self.debug:
                    self.saycrit(msg)
                raise e
            self.die(msg)

    def _getbdcommon(self, match):
        count = 0
        while True:
            candidate = [ m for m in glob.glob(match) if '-part' not in m ]
            assert len(candidate) < 2
            if len(candidate) > 0:
                return os.path.realpath(candidate[0])
            else:
                time.sleep(0.1)
                count += 1
            if count > 10:
                break

    def getbd(self, wwn):
        '''wwn: str wwn from virtual device
        returns str path to block device in Linux'''
        # workaround for udev re-creating symlinks (just ask more times)
        result = None
        match = '/dev/disk/by-id/wwn*{w}*'.format(w = wwn)
        return self._getbdcommon(match)

    def getbdpci(self, pciaddr, vdid):
        '''pciaddr: str for PCI Address of the controller in the form xx:xx:xx:xx
        vdid: int ID of the Virtual disk (needed for the scsi-x:x:vdid:x contstruct)
        returns str path to block device in Linux'''
        result = None
        pspl = pciaddr.split(':')
        pdom = pspl[0] # the PCI domain
        pbus = pspl[1] # the PCI bus
        pdev = pspl[2] # the PCI device
        pfun = int(pspl[3], 0) # the PCI function (single digit int)
        match = '/dev/disk/by-path/pci-*{pd}:{pb}:{pv}.{pf}-scsi-*:2:{v}:*'.format(pd = pdom.zfill(4), pb = pbus, pv = pdev, pf = pfun, v = vdid)
        return self._getbdcommon(match)

class Controller(MCommon):
    """
    Main Controller class

    properties
    self.ctrlid: int controller ID (e.g. as in /c0)
    """

    def __init__(self, ctrlid, binname = None, physicaldisks = None, simulate = True, debug = False):
        super(Controller, self).__init__(simulate, debug = debug)
        self.ctrlid = ctrlid
        self.binname = binname
        cmd = '{b} /c{c} show j'.format(b = self.binname, c = self.ctrlid)
        self.j = self.get_json(cmd)
        self.driver = self._getdriver()
        if self.binname == None:
            self.binname = self._getbinname()
        self.physicaldisks = physicaldisks
        if self.physicaldisks == None:
            self.physicaldisks = self._getphysicaldisks()
        # self.pciaddr = pciaddr

    @property
    def model(self):
        return self.j['Controllers'][0]['Response Data'][u'Product Name']

    @property
    def pciaddr(self):
        return self.j['Controllers'][0]['Response Data'][u'PCI Address']

    def _getphysicaldisks(self):
        # TODO
        # import pdb; pdb.set_trace()
        # self.die('Not implemented')
        pass

    def _getdriver(self):
        return self.j['Controllers'][0]['Response Data'][u'Driver Name']

    def _getbinname(self):
        # TODO - choose binname according to driver/model name
        # import pdb; pdb.set_trace()
        # self.die('Not implemented')
        pass

class PhysDisk(MCommon):
    """physical disk or solid state drive class
    Used as a child object for Controller (LSI or PERC) class object instances
    properties:
    self.binname - path to binary tool (e.g. /usr/bin/storcli64)
    self.ituple - (int controllerID, int enclosureID, int slotID)
    self.ctrlid, self.enclid, self.slotid = self.ituple
    self.virtualdevs - list of VirtualDev objects

    A PhysDisk objects might have up to two VirtualDev class object instances (two with journal)
    """

    def __init__(self, ituple, binname = None, simulate = True, virtualdevs = None, debug = False):
        super(PhysDisk, self).__init__(simulate, debug = debug)
        self.ituple = ituple
        if self.ituple[1] == '':
            self.identifier = '/c{c}/s{s}'.format(c = self.ituple[0], s = self.ituple[2])
        else:
            self.identifier = '/c{c}/e{e}/s{s}'.format(c = self.ituple[0], e = self.ituple[1], s = self.ituple[2])
        self.binname = binname
        self.simulate = simulate
        self.ctrlid, self.enclid, self.slotid = self.ituple
        self.diskgrp = self._get_diskgrp()
        self.debug = debug
        self.virtualdevs = virtualdevs
        if virtualdevs == None:
            self.virtualdevs = self.getvirtualdevs()

    def __str__(self):
        return self.identifier

    @property
    def numvirtualdevs(self):
        return len(self.getvirtualdevs())

    @property
    def size(self):
        '''returns the "Coerced size" in the controller for self.ituple'''
        cmd = '{t} {i} show all j'.format(t = self.binname, i = self.identifier)
        # get the json output
        j = self.get_json(cmd)
        devkey = 'Drive {i} - Detailed Information'.format(i = self.identifier)
        devkeyattr = 'Drive {i} Device attributes'.format(i = self.identifier)
        csize = j['Controllers'][0]['Response Data'][devkey][devkeyattr]['Coerced size']
        lsectorsize = j['Controllers'][0]['Response Data'][devkey][devkeyattr][u'Logical Sector Size']
    	# # "Coerced size" : "3.637 TB [0x1d1b00000 Sectors]",
        if 'Sectors' not in csize:
            self.die('Something went wrong, could not get coerced size:\n{s}'.format(s = csize))
        try:
            size = [ i for i in re.split('[\s\[]+', csize) if i.startswith('0x') ][0]
        except Exception as e:
            self.die(e)
        if lsectorsize == u'4 KB':
            ssize = 4096
        elif lsectorsize == u'512B':
            ssize = 512
        else:
            self.die('# Unknown logical sector size {l}'.format(l = lsectorsize))
        # # int('0x1d1b00000', 0) * 512 # converting from hex sectors to bytes
        return int(size, 0) * ssize

    @property
    def parent(self):
        return Controller(self.ctrlid, binname = self.binname, simulate = self.simulate, debug = self.debug)

    def _get_diskgrp(self):
        '''returns int DG for this ituple'''
        j = self.parent.j
        pdlist = j['Controllers'][0]['Response Data']["PD LIST"]
        if self.enclid == '':
            meid = ' '
        else:
            meid = self.enclid
        match = '{e}:{s}'.format(e = meid, s = self.slotid)
        filt = lambda x: x[u'EID:Slt'].startswith(match)
        try:
            return filter(filt, pdlist)[0][u'DG']
        except IndexError as e:
            self.die('Failed to get disk group for {d},\ncmd:\n{c}'.format(d = self, c = cmd))

    def getvirtualdevs(self):
        '''
        returns list with virtual devices for this identifier
        '''
        allvds = []
        cmd = '{t} /c{c}/vall show j'.format(t = self.binname, c = self.ctrlid)
        j = self.get_json(cmd)
        try:
            vdrives = j['Controllers'][0]['Response Data']['Virtual Drives']
        except KeyError as e:
            if e.message == 'Response Data':
                # no virtual devices at all (happens with a single physical disk)
                return allvds
        match = '{s}/'.format(s = self._get_diskgrp())
        f = lambda x: x[u'DG/VD'].startswith(match)
        for vd in filter(f, vdrives):
            resvd = vd.copy()
            # get virtual disk id
            vdid = int(vd[u'DG/VD'].split('/')[-1])
            # get additional Information from the controller
            cmd = '{t} /c{c}/v{v} show all j'.format(t = self.binname, c = self.ctrlid, v = vdid)
            j = self.get_json(cmd)
            vkey = 'VD{v} Properties'.format(v = vdid)
            properties = j['Controllers'][0]['Response Data'][vkey]
            for key in properties.keys():
                resvd[key] = properties[key]
            if resvd[u'Exposed to OS'] == u'Yes':
                path = self.getbdpci(self.parent.pciaddr, vdid)
                # double check if wwn is available as well
                if resvd.has_key(u'SCSI NAA Id'):
                    wwn = resvd[u'SCSI NAA Id']
                    assert path == self.getbd(wwn)
                allvds.append(VirtualDev(path, hidden = False, vdid = vdid, ituple = self.ituple, simulate = self.simulate, debug = self.debug))
            else:
                allvds.append(VirtualDev(path = None, hidden = True, vdid = vdid, ituple = self.ituple, simulate = self.simulate, debug = self.debug))
        return allvds

    def unhidevd(self, vdev):
        '''vdev: VirtualDev instance
        performs unhide operation on vdev'''
        cmd = '{t} /c{c}/v{v} set hidden=off'.format(t = self.binname, c = self.ctrlid, v = vdev.vdid)
        assert vdev.hidden
        self.run(cmd, simulate = self.simulate)

    def addvd(self, size = None, wbc = True):
        '''Creates a virtual device
        size: int size of the virtual device in bytes, if None assumes maximum available size
        wbc: bool write back cache, default True ('wrcache = wb')
        '''
        # ensure there is at most one virtual device:
        priornumvds = self.numvirtualdevs
        assert priornumvds < 2
        # ex. with size
        # storcli64 /c0 add vd type=r0 Size=5722524 drives=252:7 pdcache=off direct nora wt
        # ex. no size
        # storcli64 /c0 add vd type=r0 drives=252:7 pdcache=off direct nora wb
        sizearg = ''
        if size:
            sizearg += 'Size={s}'.format(s = size / 1024 ** 2)
        if wbc:
            wb = 'wb'
        else:
            wb = 'wt'
        if self.enclid == '':
            cmd = '{t} /c{c} add vd type=r0 {sz} drives={s} pdcache=off direct nora {w}'.format(t = self.binname, c = self.ctrlid, sz = sizearg, s = self.slotid, w = wb)
        else:
            cmd = '{t} /c{c} add vd type=r0 {sz} drives={e}:{s} pdcache=off direct nora {w}'.format(t = self.binname, c = self.ctrlid, sz = sizearg, e = self.enclid, s = self.slotid, w = wb)
        out = self.run(cmd, simulate = self.simulate)
        if not self.simulate and 'Success' not in out:
            self.die('Something went wrong, please check:\nCommand:\n{c}\nOutput:\n{o}'.format(c = cmd, o = out))
        if not self.simulate:
            expectednumvds = priornumvds + 1
            count = 0
            while priornumvds < expectednumvds:
                time.sleep(1 + (0.1 * count))
                priornumvds = self.numvirtualdevs
                count += 1
                if count > 5:
                    # will wait ~5.5 seconds at most
                    self.die('Timed out waiting for new virtual device on {d}'.format(d = self.identifier))

    def delvd(self, virtualdev):
        '''deletes virtualdev instance'''
        # uses force, otherwise will fail due to the valid MBR
        cmd = '{t} /c{c}/v{v} del force'.format(t = self.binname, c = self.ctrlid, v = virtualdev.vdid)
        self.run(cmd, simulate = self.simulate)

    def shrinkvd(self, vdev, newsize = None):
        '''vdev: VirtualDev instance
        newsize: int new size in bytes (default 100MB)
        '''
        if newsize == None:
            newsize = vdev.size - 100 * 1024 ** 2
        # delete virtualdevice
        self.delvd(vdev)
        self.addvd(size = newsize, wbc = False)

class BDCommon(MCommon):
    """simple class for common methods inheritance for BlockDevice and Partition classes, shares methods from MCommon

    self.path - str. path to block device, e.g. /dev/sdx
    self.name - str. name, e.g. sdx
    self.wwnpath - str path to wwn, e.g. /dev/disk/by-id/wwn-* symlink pointing to /dev/sdx
    self.simulate - common property for whether an execution will take place
    """

    def __init__(self, path, simulate = True, debug = False):
        super(BDCommon, self).__init__(simulate, debug)
        self.path = path # e.g. /dev/sda
        self.name = self.path.split('/')[-1]
        self.debug = debug

    def __str__(self):
        return self.path

    def __repr__(self):
        return '{n}("{p}")'.format(n = self.__class__.__name__,p = self.path)

    def gettool(self, name):
        '''name: str name of the tool
        returns path to tool or non if none found'''
        tool = find_executable(name)
        if not tool:
            self.die("I need {s}, but it doesn't seem to be installed, or not in PATH, please check".format(s = name))
        return tool

    @retry(OSError, 3, 0.1, 1) # workaround for an OSError race
    def get_size(self):
        "Get the file size by seeking at end"
        fd = os.open(self.path, os.O_RDONLY)
        try:
            return os.lseek(fd, 0, os.SEEK_END)
        finally:
            os.close(fd)

    @property
    @retry(RetryException, 5, 0.1, 1) # workaround for an OSError race
    def in_use(self):
        used = True
        try:
            desc = os.open(self.path, os.O_EXCL)
            if desc:
                os.close(desc)
                return False
        except OSError as e:
            if e.errno == 2:
                raise RetryException
            return used

    @property
    def vendor(self):
        bdev = os.path.basename(self.path)
        spath = '/sys/class/block/{dev}/device/vendor'.format(dev = bdev)
        vendor = open(spath).read().rstrip('\n').strip().lower()
        return vendor

    @property
    def spinitdisk(self):
        return self.gettool('storpool_initdisk')

    @property
    def parted(self):
        return self.gettool('parted')

    @property
    def sgdisk(self):
        return self.gettool('sgdisk')

    @property
    def partprobe(self):
        return self.gettool('partprobe')

    @property
    def need_resize(self):
        return self.gettool('./need_resize.sh')

    @property
    def wwnpath(self):
        '''returns path to wwn symlink'''
        for i in range(10):
            # retry 10 times
            for wwn in glob.glob('/dev/disk/by-id/wwn*'):
                if os.path.realpath(wwn) == self.path:
                    return wwn

    def spconst(self):
        '''returns the output from ``storpool_initdisk --list``'''
        cmd = '{i} --list'.format(i = self.spinitdisk)
        alllines = self.run(cmd, simulate = False) # safe command
        for line in alllines.split('\n'):
            spl = line.split(',')
            if len(spl) == 1:
                if spl[0] == '' or spl[0] == 'Done.':
                    continue
            if spl[0] == self.path:
                return spl

class VirtualDev(BDCommon):
    """VirtualDev instance object - the bond between PhysDisk and BlockDevice instances

    self.path - str path to block device in Linux
    self.vdid - int virtual disk ID from the controller
    self.ituple - (ctrl, enclosure, slot) IDs
    self.hidden - bool if true does not initialise from BDCommon instance
    self.binname - name of the tool to query the controller
    self.parent - parent PhysDisk object instance
    """

    def __init__(self, path, hidden, vdid = None, ituple = None, simulate = True, debug = False):
        self.path = path
        self.hidden = hidden
        self.ituple = ituple
        self.vdid = vdid
        self.simulate = simulate
        self.debug = debug
        if not self.hidden:
            # inherit Linux block device properties as well
            super(VirtualDev, self).__init__(self.path, self.simulate, debug = self.debug)
            self.ituple = self.get_ituple()
        # ensure we have either vdid or path, never none of the two
        assert self.vdid or self.path
        if self.vdid == None:
            self.vdid = self.get_vdid()
        # ensure either we have path or the instance is hidden
        assert self.path or self.hidden
        self.identifier = '/c{c}/v{v}'.format(c = self.ituple[0], v = self.vdid)

    def __str__(self):
        if self.path:
            return self.path
        else:
            return self.identifier

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.hidden and other.hidden:
            return ((self.vdid, self.ituple) == (other.vdid, other.ituple))
        elif not self.hidden and not other.hidden:
            # both visible to OS
            return ((self.path, self.ituple) == (other.path, other.ituple))

    def __ne__(self, other):
        return not self == other

    def gettoolversion(self, tool):
        '''tool: str path to tool
        returns tool version in tuple, e.g.
        '''
        tool = self.gettool('storcli64')
        cmd = '{t} -v'.format(t = tool)
        try:
            versionline = [ el for el in self.run(cmd, simulate = False).split('\n') if ' Ver ' in el ][0].split()
        except IndexError as e:
            self.die('Unable to get version for {t}, command was {c}'.format(t = tool, c = cmd))
        v, vmajor, vminor = [ int(i) for i in versionline[versionline.index('Ver')+1].split('.') ]
        return (v, vmajor, vminor)

    @property
    def binname(self):
        if self.hidden:
            # no vendor/binname if device is hidden
            return
        if 'lsi' in self.vendor or 'avago' in self.vendor:
            tool = self.gettool('storcli64')
            ver, mj, mn = self.gettoolversion(tool)
            minver = 1
            minmj = 16
            if ver < minver or (ver == minver and mj < minmj):
                self.die('{t} version is {va}.{vb}.{vc}, minimum required {ra}.{rb}'.format(t = tool, va = ver, vb = mj, vc = mn, ra = minver, rb = minmj))
            return tool
        elif 'dell' in self.vendor:
            return self.gettool('perccli64')
        else:
            self.die('Unsupported vendor {v}'.format(v = self.vendor))

    @property
    def parent(self):
        return PhysDisk(self.ituple, binname = self.binname, simulate = self.simulate, debug = self.debug)

    @property
    def child(self):
        return BlockDevice(self.path, simulate = self.simulate, debug = self.debug)

    @property
    def size(self):
        return self.get_size()

    def get_size(self):
        '''returns the size of the block device, else'''
        if self.hidden:
            self.die('# Please unhide {s} to proceed'.format(s = self))
        else:
            # return size of the child BlockDevice
            return self.child.get_size()

    def setwb(self):
        cmd = '{t} /c{c}/v{v} set wrcache=WB'.format(t = self.binname, c = self.ituple[0], v = self.vdid)
        self.run(cmd, simulate = self.simulate)

    def setwt(self):
        cmd = '{t} /c{c}/v{v} set wrcache=WT'.format(t = self.binname, c = self.ituple[0], v = self.vdid)
        self.run(cmd, simulate = self.simulate)

    def get_vdid(self):
        # iterate to our instance in parent.virtualdevs
        for inst in self.parent.virtualdevs:
            if self == inst:
                return inst.vdid
        # debug if none of the parent instances is this one
        raise

    def get_ituple(self):
        '''get ctrl, eid, slotid tuple and virtual disk ID'''
        if self.hidden:
            raise
        self.storclihelper = self.gettool('/usr/lib/storpool/storcli-helper.pl')
        args = '-p {t}'.format(t = self.binname)
        cmd = '{s} {a} {b}'.format(s = self.storclihelper, a = args, b = self.path)
        rawout = self.run(cmd, simulate = False).split('\n') # safe
        data = {}
        for line in rawout:
            # omit empty lines
            if line == '':
                continue
            # parse variables
            key, value = line.split('=')
            data[key.strip()] = value.strip().strip("'")
        ID_SERIAL = data['ID_SERIAL']
        ID_MODEL = data['ID_MODEL']
        self.parentidserial = ID_SERIAL
        self.parentidmodel = ID_MODEL
        try:
            ID_ENCLOSURE = data['ID_ENCLOSURE']
            ID_SLOT = data['ID_SLOT']
            ID_CTRL = data['ID_CTRL']
            ID_VDID = data['ID_VDID']
        except KeyError as e:
            self.die('Please check if correct version of {s} is installed'.format(s = self.storclihelper))
        self.ituple = (ID_CTRL, ID_ENCLOSURE, ID_SLOT)
        self.vdid = ID_VDID
        return self.ituple

class BlockDevice(BDCommon):
    """A generic object for a Linux Block Device
    properties:
    self.partitions - list with child Partition objects for this block device (e.g. /dev/sdx1)
    """

    def __init__(self, path, simulate = True, debug = False):
        super(BlockDevice, self).__init__(path, simulate)
        try:
            self.devmode = os.stat(self.path).st_mode
        except OSError as e:
            self.die(e)
        if not stat.S_ISBLK(self.devmode):
            self.die("{d} not block device?".format(d = self.path))
        self.debug = debug
        self.simulate = simulate

    @property
    def parentvd(self):
        '''returns VirtualDev object instance in case of a supported binname'''
        return VirtualDev(self.path, hidden = False, vdid = None, ituple = None, simulate = self.simulate, debug = self.debug)

    @property
    def child(self):
        try:
            return self.partitions[0]
        except IndexError:
            return None

    @property
    def partitions(self):
        '''returns list of Partition objects for this block device'''
        partitions = []
        for i in range(10):
            for dev in glob.glob('/dev/*'):
                if dev.startswith(self.path):
                    if dev == self.path:
                        # exlude block device
                        continue
                    if dev in [i.path for i in partitions]:
                        # checks if already added
                        continue
                    partitions.append(Partition(dev, simulate = self.simulate, debug = self.debug))
        if len(partitions) > 1:
            self.saycrit('\n'.join([ str(i) for i in partitions]))
            self.die('More than one partition found on {d}, unsupported, exiting...'.format(d = self.path))
        return partitions

    @property
    def backup(self):
        '''collects backup dump from sgdisk in a tempfile'''
        tbackup = tempfile.NamedTemporaryFile(prefix='{d}-partition-table-backup-'.format(d = self.name), delete=False) # keeps the backup file in tmp
        cmd = '{s} --backup={b} {d}'.format(s = self.sgdisk, b = tbackup.name, d = self.path)
        self.run(cmd, simulate = False) # safe command
        return tbackup

    # def waitpart(self): # don't use for now
    #     '''wait for the partition to become available, to be used in addpart method... eventually
    #     '''
    #     if self.simulate:
    #         return
    #     count = 0
    #     while len(self.partitions) < 1:
    #         time.sleep(0.1)
    #         count += 1
    #         if count == 10:
    #             break

    def restore(self, tbackup):
        '''restores the partition table from a backupfile'''
        cmd = '{s} --load-backup={b} {d}'.format(s = self.sgdisk, b = tbackup.name, d = self.path)
        self.run(cmd, simulate = self.simulate)

    def addpart(self, start = None, end = None, parttype = None):
        if self.in_use:
            if not self.simulate:
                self.die('{s} is being used, bailing out'.format(s = self))
        if start == None:
            start = '2M'
        if end == None:
            end = '100%'
        if parttype == None:
            parttype = 'gpt'
        # parted -s --align optimal /dev/${DRIVE} mklabel gpt -- mkpart primary 2M 100%
        cmd = '{p} -s --align optimal {d} mklabel {pt} -- mkpart primary {s} {e}'.format(p = self.parted, d = self.path, s = start, e = end, pt = parttype)
        self.run(cmd, simulate = self.simulate)
        # trigger partprobe to update the kernel partition table for this device
        pprobecmd = '{p} {d}'.format(p = self.partprobe, d = self.path)
        self.run(pprobecmd, simulate = self.simulate)

    def dump(self):
        '''returns tuple(start, end, parttable) in (bytes, bytes, str) for the partition object'''
        cmd = '{p} -s -m {d} -- unit B print'.format(p = self.parted, d = self.path)
        # # parted -m /dev/sdc -- unit B print
        # BYT;
        # /dev/sdc:1000204886016B:scsi:512:512:gpt:ATA Hitachi HUA72201:;
        # 1:1048576B:1000204140543B:1000203091968B::primary:msftdata;
        tbackuphr = tempfile.NamedTemporaryFile(prefix='{d}-partition-table-human-readable-'.format(d = self.name), delete=False) # keeps the human readable output of parted in /tmp
        res = self.run(cmd, simulate = False)
        with open(tbackuphr.name, 'w') as b:
            b.write(res)
        res = res.replace('\n','').split(';') # strip \n and split by ;
        lines = [ i for i in res if i != '' ] # remove empty lines
        semilastline = lines[-2]
        parttable = semilastline.split(':')[5]
        lastline = lines[-1]
        spl = lastline.split(':')
        return (spl[1], spl[2], parttable)

class Partition(BDCommon):
    """A Linux partition object
    properties:
    self.start - byte where the partition starts on the parent block device
    self.end - byte where the partition ends on the parent block device

    methods:
    self.shrink:
     - checks if there is only one partition on the parent block device (else dies)
     - dumps the partition table of the parent block device
     - gets the start/end of the partition
     - executes partition removal and recreation with the same start and the new end
         - if successful updates self.end
         - if not restores the parent partition table from the backup
    """

    def __init__(self, path, simulate = True, debug = False):
        super(Partition, self).__init__(path, simulate, debug)
        p = re.compile('/dev/sd[a-z]+\d+$')
        m = p.match(self.path)
        if not m:
            self.die('{p} does not look like a partition').format(p = self.path)
        self.debug = debug
        self._bdname = self.path.rstrip(string.digits)
        self.parent = BlockDevice(self._bdname, simulate = self.simulate, debug = self.debug)
        self.start, self.end, self.ptype = self.parent.dump()

    def shrink(self):
        '''performs shrink on the partition with 100*1024**2 (100 MB)'''
        # get backup on the parent block device partition table
        diff = 100 * 1024 ** 2 # 100MB in bytes
        msize = self.get_size()
        psize = self.parent.get_size()
        if psize - msize >= diff:
            self.say('{p} already shrunk, proceeding'.format(p = self))
            return
        tbackup = self.parent.backup
        try:
            # removing the old partition
            cmd = '{p} {b} -- rm 1'.format(p = self.parted, b = self.parent.path)
            self.run(cmd, simulate = self.simulate, fail = True)
        except subprocess.CalledProcessError as e:
            self.saycrit('Attempting to restore partition table from {b}'.format(b = tbackup.name))
            self.parent.restore(tbackup)
        # create the new smaller partition
        try:
            newend = int(self.end.rstrip('B')) - diff
            newendstr = str(newend) + 'B'
            shrinkcmd = '{p} {b} -- mkpart primary {st} {nend}'.format(p = self.parted, b = self.parent.path, st = self.start, nend = newendstr)
            self.run(shrinkcmd, simulate = self.simulate, fail = True)
            self.end = newendstr
        except subprocess.CalledProcessError as e:
            self.saycrit('Attempting to restore partition table from {b}'.format(b = tbackup.name))
            self.parent.restore(tbackup)
            die('Shrinking failed')
        if not self.simulate:
            self.say('Success shrinking {p}'.format(p = self.path))

class StorPoolDisk(BDCommon):
    """StorPoolDisk object
    gets the output from storpool_initdisk --list and filters the line with the expected block device or partition (e.g. /dev/sdx1 or /dev/sdx)

    example 'splitline' output from `storpool_initdisk --li`
    ['/dev/sdc1', ' diskId 1688', ' version 10007', ' server instance 0', ' cluster a.o', ' WBC']
    properties
    self.cluster - cluster ID
    self.did - diskId
    self.flags - disk flags
    self.instance - server instance
    self.is_partition - bool true if self.path is Partition
    self.line - the above split line from `storpool_initdisk --list`
    self.path - path to block device or partition
    self.version - version of the onDisk format
    self.virtualdev - parent virtualdev Instance

    methods:
    self.shrink
        - if parent device is a Partition, first shrinks the partition, then resizes the parent virtual device, else just the virtual device
    """

    def __init__(self, device, size = None, simulate = True, debug = False):
        super(StorPoolDisk, self).__init__(device, simulate, debug)
        self.debug = debug
        self.line = self.spconst()
        self.simulate = simulate
        if not self.line:
            self.die('{p} not a StorPool disk'.format(p = self.path))
        assert self.path == self.line[0]
        self.did = self.line[1].split()[-1]
        self.version = int(self.line[2].split()[-1])
        self.size = size
        if self.version == 10006:
            self.instance = self.cluster = None
            if len(self.line) < 4:
                self.flags = []
            else:
                self.flags = [ i.strip() for i in self.line[3:] ]
        elif self.version == 10007:
            self.instance = int(self.line[3].split()[-1])
            self.cluster = self.line[4].split()[-1]
            self.flags = [ i.strip() for i in self.line[5:] ]
        if self.size == None:
            self.size = self.get_size()
        if self.is_partition:
            self.parent = Partition(self.path, simulate = self.simulate, debug = self.debug)
        else:
            self.parent = BlockDevice(self.path, simulate = self.simulate, debug = self.debug)
        # set size limit constants (int in bytes)
        self.lower = 100 * 1024 ** 2 # 100MB lower limit
        self.higher = 1024 * 1024 ** 2 # 1G higher limit

    def __repr__(self):
        '''
        returns string that would create  the same object.
        '''
        return 'StorPoolDisk({l})'.format(l = self.line)

    def __str__(self):
        return self.did

    @property
    def journal(self):
        '''if size less than 1G return True, needed to recognise journal disks'''
        return self.size <= self.higher

    @property
    def ssd(self):
        if self.flags is None:
            return
        elif 'SSD' in self.flags:
            return True

    @property
    def is_partition(self):
        p = re.compile('/dev/sd[a-z]+\d+$')
        m = p.match(self.path)
        if m:
            return True

    @property
    def virtualdev(self):
        '''direct link to parent VirtualDev instance'''
        if self.is_partition:
            return self.parent.parent.parentvd
        else:
            return self.parent.parentvd

    @property
    def journaldev(self):
        allvirtualdevs = self.virtualdev.parent.virtualdevs
        return filter((lambda x: x != self.virtualdev), allvirtualdevs)[0]

    @property
    def resize(self):
        cmd = '{n} {p}'.format(n = self.need_resize, p = self.path)
        try:
            self.run(cmd, simulate = False, fail = True) # safe command
        except subprocess.CalledProcessError as e:
            if e.returncode == 5:
                return True
            elif e.returncode == 6:
                return False
            else:
                self.die('{c} returned {e} (please check `bash -x {c}`)'.format(c = cmd, e = e.returncode))
    def setjournal(self, journaldev = None):
        '''journaldev: None or VirtualDev instance to be used for journal
        if journaldev is missing(None):
            - checks if the primary device has to be shrinked and executes self.shrink()
            - creates journaldev
        then:
            - sets WT on primaryvd
            - sets WB on journaldev
            - adds partition on journaldev
        '''
        if self.in_use:
            if self.simulate:
                self.saycrit("# Disk {d} with ID {id} is being used, please check if a StorPool instance isn't already running, before proceeding with --execute".format(d = self.path, id = self.did))
            else:
                self.die("Disk {d} with ID {id} is being used, please check if a StorPool instance isn't already running.".format(d = self.path, id = self.did))
        if self.ssd:
            self.die('{d} is an SSD drive, setting journal is not supported'.format(d = self))
        if self.journal:
            self.die('{d} is a journal device for {id}, bailing out'.format(d = self.path, id = self.did))
        if journaldev == None:
            # no journaldev provided, check if one exists
            pphysical = self.virtualdev.parent
            # get the parent physical device
            allvirtualdevs = pphysical.virtualdevs
            numvirtualdevs = len(allvirtualdevs)
            if numvirtualdevs > 2:
                exit('Unsupported number of virtual devices for {p}'.format(p = pphysical))
            elif numvirtualdevs == 2:
                journaldev = filter((lambda x: x != self.virtualdev), allvirtualdevs)[0]
                if self.debug:
                    self.say(journaldev)
                # check if the "journal" is hidden and unhide
                if journaldev.hidden:
                    pphysical.unhidevd(journaldev)
                    journaldev = self.journaldev # get unhidden journaldev
                # and has the right size
                if journaldev.size > self.higher or journaldev.size < self.lower:
                    self.die('{j} size is not within expected limits: {s}\n(limits lower/higher: {l}/{h} )'.format(j = journaldev, s = journaldev.size, l = self.lower, h = self.higher))
            elif numvirtualdevs < 2:
                # check if there is enough size difference
                diffsize = pphysical.size - self.virtualdev.size
                if diffsize < self.lower:
                    # not enough space to create the virtual device
                    self.shrink()
                if diffsize > self.higher:
                    # Unexpected, bail out
                    self.die('Unexpected size difference for {v}, more than {h}M, smaller than {p}'.format(v = self.virtualdev, h = self.higher / 1024 ** 2, p = pphysical))
                # enough space, create the journal virtual device
                pphysical.addvd()
                if self.simulate:
                    self.die('# Please create the journal virtual device to proceed.')
                journaldev = self.journaldev # get the newly created journaldev
        # check if a partition has to be created
        bd = journaldev.child
        part = bd.child
        if part == None:
            bd.addpart(end = '-2M')
            part = bd.child
        # set WT on primary virtualdev
        self.virtualdev.setwt()
        # set WB on journal virtualdev
        journaldev.setwb()
        if self.simulate:
            part = bd.wwnpath + '-part1'
        cmd = '{s} -r --journal {j} {id} {p}'.format(s = self.spinitdisk, j = part, id = self.did, p = self.path)
        self.run(cmd, simulate = self.simulate)

    def shrink(self):
        if not self.resize:
            return
        ptrigger = self.is_partition
        if ptrigger:
            self.parent.shrink()
            start, end, ptype = self.parent.parent.dump()
        # shrink parent virtual device as well:
        self.virtualdev.parent.shrinkvd(self.virtualdev)
        if ptrigger:
            # # re-create the partition
            if ptype == 'gpt':
                self.virtualdev.child.addpart(start = self.parent.start, end = self.parent.end, parttype = 'gpt')
            else:
                self.say('# Partition type not "gpt", will not re-create the partition table')
