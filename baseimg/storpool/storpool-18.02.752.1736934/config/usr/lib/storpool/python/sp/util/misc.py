"""Provides miscellaneous utilities."""

from ConfigParser import ConfigParser
import itertools
import os
import re
import socket
import sys


from sp.util import decorators
from sp.util import re_extensions as extre
from sp.util.backports import subprocess


def list2d_flatten(lst):
    """Flatten a list of lists."""
    return list(itertools.chain(*lst))


def is_systemd():
    """Indicates whether the machine runs systemd."""
    return os.path.isdir('/run/systemd/system')


def get_runlevel():
    """ Get the system runlevel (hopefully 1 through 5). """
    out = subprocess.check_output(['runlevel']).decode('UTF-8')
    lines = out.rstrip().split('\n')
    assert len(lines) == 1
    fields = lines[0].split()
    assert len(fields) == 2
    return int(fields[1])


def is_exe(fpath):
    """Checks whether the given file path exists and is executable."""
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


def which(program):
    """Finds and executable path for `program`."""
    fpath, _ = os.path.split(program)
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


def get_memtotal_kb():
    """Returns total machine memory in KB."""
    totalmem_m = re.compile(r"MemTotal:\s*(?P<mem>\d+) kB")
    with open('/proc/meminfo', 'r') as meminfof:
        lines = meminfof.readlines()
    match = extre.matches(totalmem_m, lines)[0]
    return int(match.group('mem'))


@decorators.timeout(seconds=10)
def scheck(tup):
    '''
    tup: tuple (host, port)
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	#create a TCP socket
    try:
        sock.connect(tup) #connect to server on the port
        sock.close()
        return True
    except Exception:
        return False


def query_yes_no(question, default=None):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes": "yes", "y": "yes", "ye": "yes",
             "no": "no", "n": "no"}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        sys.stdout.flush()
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def sp_mver():
    """Returns StorPool major version as a tuple of two integers(e.g. (18, 2))."""
    parser = ConfigParser()
    parser.read('/etc/storpool_version.ini')
    ver = parser.get('source', 'version')
    return tuple(int(num) for num in ver.split('.')[:2])
