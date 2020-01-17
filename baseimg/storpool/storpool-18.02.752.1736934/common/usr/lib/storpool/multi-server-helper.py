#!/usr/bin/env python
import argparse
import os
import sys

from sp.util.backports import subprocess


class StorPoolDisk(object):
    """StorPoolDisk object
    example 'splitline' output from `storpool_initdisk --li`
    ['/dev/sdc1', ' diskId 1688', ' version 10007', ' server instance 0', ' cluster a.o', ' WBC']
    properties
    self.line - the above split line from `storpool_initdisk --list`
    self.blockp - path to block device
    self.did - diskId
    self.version - version of the onDisk format
    self.instance - server instance
    self.cluster - cluster ID
    self.flags - disk flags
    """
    def __init__(self, line):
        super(StorPoolDisk, self).__init__()
        self.line = line
        self.blockp = line[0]
        self.did = line[1].split()[-1]
        self.version = int(line[2].split()[-1])
        if self.version == 10006:
            self.instance = self.cluster = None
            self.flags = [ i.strip() for i in line[3:] ]
        elif self.version == 10007:
            self.instance = int(line[3].split()[-1])
            self.cluster = line[4].split()[-1]
            self.flags = [ i.strip() for i in line[5:] ]
        else:
            self.version = None
            self.instance = self.cluster = self.flags = self.ssd = None
    def __repr__(self):
        '''
        returns string that would create  the same object.
        '''
        return 'StorPoolDisk({l})'.format(l = self.line)
    def __str__(self):
        '''
        shows all variables returned by __init__ in a tuple
        '''
        return str((self.blockp, self.did, self.instance, self.cluster, self.flags, self.ssd))
    @property
    def ssd(self):
        if self.flags is None:
            return
        elif 'SSD' in self.flags:
            return True
    @property
    def journal(self):
        for i in self.flags:
            if 'journal' in i:
                return True
    @property
    def jmv(self):
        for i in self.flags:
            if 'mv' in i or 'jmv' in i:
                return i.split()[-1]
    @property
    def journaldev(self):
        self.alldisks = const()
        for disk in self.alldisks:
            try:
                if self.jmv in disk.flags[-1] and 'journal' in disk.flags[-1]:
                    return disk
            except IndexError as e:
                pass
    @property
    def ejected(self):
        if 'EJECTED' in self.flags:
            return True

def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

def const():
    '''
    returns list with StorPoolDisk objects constructed from `storpool_initdisk --list`
    '''
    # get the output
    result = []
    try:
        cmd = '{i} --list'.format(i = initdisk).split()
        alllines = subprocess.check_output(cmd, stderr = None)
    except subprocess.CalledProcessError as e:
        exit(e)
    for line in alllines.split('\n'):
        spl = line.split(',')
        if len(spl) == 1:
            if spl[0] == '' or spl[0] == 'Done.':
                continue
        result.append(StorPoolDisk(spl))
    return result

def chunks(l, n):
    '''
    Yield successive n-sized chunks from l
    '''
    for i in range(0, len(l), n):
        yield l[i:i + n]

def commands(disks, instances, mod = None):
    '''
    disks: list of StorPoolDisk objects
    instances: int - number of desired server instances
    prints commands needed to disperse over instances
    '''
    def p(slices, inst, mod = None):
        disks = slices.pop()
        if mod:
		inst += mod
        for disk in disks:
            if disk.journal:
                continue # never print a journal
            jarg = ''
            if disk.jmv:
                jarg = '--journal {j}'.format(j = disk.journaldev.blockp)
            print '{s} -r -i {i} {did} {b} {j} # {ssd}'.format(s = initdisk, i = inst, did = disk.did, b = disk.blockp, ssd = ' '.join(disk.flags), j = jarg)
    sl = len(disks)/instances
    slices = [ i for i in chunks(disks, sl) ]
    for inst in range(instances):
        p(slices, inst, mod)
    for inst in range(len(slices)):
        p(slices, inst, mod)

def main(instances, bytype = None):
    '''
    instances: int - number of instances
    '''
    disks = const()
    alldisks = filter((lambda x: not x.journal and not x.ejected), disks) # exclude journal and ejected drives

    if len(alldisks) < instances:
        exit('Need at least {i} disks, have {d}'.format(i = instances, d = len(alldisks)))
    elif len(alldisks) == instances:
        commands(alldisks, instances)
    else:
        ssds = filter((lambda x: x.ssd), alldisks)
        hdds = filter((lambda x: not x.ssd), alldisks)
	if bytype:
		commands(ssds, 1)
		commands(hdds, instances - 1, 1)
	else:
	        if len(ssds) < instances or len(hdds) < instances:
	            commands(alldisks, instances)
	        else:
	            commands(ssds, instances)
	            commands(hdds, instances)

if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='''
        Prints relevant commands for dispersing the drives to multiple server instances\
        ''')
        parser.add_argument('-i', '--instances', type = int, help="Number of instances", default = 2)
        parser.add_argument('-b', '--bytype', help="Split by type - one SSD only instance plus i-1 HDD instances (default False)", default = False, action = 'store_true')
        args = parser.parse_args()
        if args.instances < 1 or args.instances > 4:
            exit('Multi-server supports 1 - 4 instances')
        initdisk = which('storpool_initdisk')
        main(args.instances, args.bytype)
    except KeyboardInterrupt as e:
        exit(e)
