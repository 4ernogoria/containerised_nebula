"""Reads and provides information about the machine socket/cpu/numa configurations."""

import collections
import re
import subprocess
import tempfile


from sp.util import re_extensions as extre
from sp.util import decorators as spd
from sp.util.file import parsers


@spd.static_vars(cpui=None)
def get(reread=False):
    """Reads the machine cpu information and returns a CPUInfo object.
    The CPUInfo object is cached, if reread flag is set, the cpu information
    will be read again and the obejct will be reconstructed.
    """
    if get.cpui is not None and not reread:
        return get.cpui
    cpuinfo_file = '/proc/cpuinfo'
    with tempfile.NamedTemporaryFile() as lscpu_file:
        subprocess.call('lscpu', stdout=lscpu_file)
        get.cpui = CPUInfo(cpuinfo_file, lscpu_file.name)
    return get.cpui


class CPUInfo(object):
    """Provides information about the machine cpus."""
    def __init__(self, CPUINFO_FILE, LSCPU_FILE):
        cpu_raw_info, self.vndr, self.fam = get_cpu_raw_info(CPUINFO_FILE)
        self.numa_to_cpus = get_numa_info(LSCPU_FILE)
        sockets = collections.defaultdict(lambda: collections.defaultdict(set))
        self.numas = len(self.numa_to_cpus.keys())
        cpus_to_numa = {}
        for numa, cpus in self.numa_to_cpus.items():
            for cpu in cpus:
                cpus_to_numa[cpu] = numa
        self.cpus = {}
        self.sockets = {}
        for phys_id, core_id, cpu in cpu_raw_info:
            sockets[phys_id][core_id].add(cpu)
            self.cpus[cpu] = (phys_id, core_id, cpus_to_numa[cpu])
        for phys_id in sockets.keys():
            self.sockets[phys_id] = dict(sockets[phys_id])

    def vendor(self):
        """Vendor of the machine processors."""
        return self.vndr

    def family(self):
        """Vendor family of the machine processors."""
        return self.fam

    def socket_count(self):
        """Number of sockets on the motherboard."""
        return len(self.sockets.keys())

    def core_count(self, phys_id):
        """Number of cores for the given socket id."""
        return len(self.sockets[phys_id].keys())

    def cpu_count(self):
        """Number of cpus accross all sockets."""
        return len(self.cpus.keys())

    def socket_info(self, physical_id):
        """Returns core-cpus dictionary for the given socket id."""
        return self.sockets[physical_id]

    def cpu_list(self, physical_id, core_id):
        """List of cpus on the given core on the given socket."""
        return list(self.sockets[physical_id][core_id])

    def numa_node_of(self, cpu):
        """Numa node of the cpu."""
        return self.cpus[cpu][2]

    def core_id_of(self, cpu):
        """The id of the core on which the given cpu is placed."""
        return self.cpus[cpu][1]

    def socket_id_of(self, cpu):
        """The id of the socket on which the given cpu is placed."""
        return self.cpus[cpu][0]

    def thread_sibling_of(self, cpu):
        """Returns the cpu that is thread-sibling to the given one.
        Returns None if there is none.(e.g. if hyperthreading is not enabled)
        """
        physical_id, core_id, _ = self.cpus[cpu]
        siblings = self.cpu_list(physical_id, core_id)
        siblings.remove(cpu)
        return None if not siblings else siblings[0]

    def add_sibling(self, cpu):
        """Returns a pair(tuple) of cpus - the given one and its thread-sibling.
        The pair is sorted.
        If the cpu does not have sibling, the pair is (cpu, None).
        """
        sibling = self.thread_sibling_of(cpu)
        if sibling is None:
            return (cpu, None)
        # the tuple() below is important so that the siblings pair is hashable
        return tuple(sorted([cpu, sibling]))

    def to_siblings_pairs(self, cpus):
        """Finds the sibling pairs for the given cpus and returns sorted list of
        the unique ones.
        """
        return sorted(set(map(self.add_sibling, cpus)))

    def numa_nodes(self):
        """Number of numa nodes on the machine."""
        return self.numas

    def is_on_first_core_of_numa(self, cpu):
        """Indicates whether the given cpu is on the first core of its numa node."""
        _, __, numa = self.cpus[cpu]
        return cpu == min(self.numa_to_cpus[numa])

    def is_first_core_of_numa(self, siblings_pair):
        """Indicates whether the given thread-siblings pair is on the first core
        of its numa node.
        """
        return self.is_on_first_core_of_numa(siblings_pair[0])

    def is_not_first_core_of_numa(self, siblings_pair):
        """Indicates whether the given thread-siblings pair is NOT on the first
        core of its numa node.
        """
        return not self.is_first_core_of_numa(siblings_pair)

    def numa_node_of_pair(self, siblings_pair):
        """Returns the numa node of the given thread-siblings pair."""
        return self.numa_node_of(siblings_pair[0])

    def hyperthreading(self):
        """Indicates whether hyperthreading is available AND enabled."""
        return self.thread_sibling_of(0) is not None

    def list_all_cpus(self):
        """Returns a list of all cpus on the machine."""
        return range(0, self.cpu_count())


VENDOR_ID_M = re.compile(r"vendor_id\s*:\s*(?P<vendor_id>\w+)")
CPU_FAMILY_M = re.compile(r"cpu family\s*:\s*(?P<family_n>\w+)")


def get_vendor(lines):
    """Returns the vendor and family of the processors, by reading
    the cpuinfo file lines.
    """
    vendor = set(match.group('vendor_id') for match in extre.matches(VENDOR_ID_M, lines)).pop()
    family = set(match.group('family_n') for match in extre.matches(CPU_FAMILY_M, lines)).pop()
    return vendor, int(family)


PROCESSOR_M = re.compile(r"processor\s*:\s*(?P<proc>\d+)")
PHYSICAL_ID_M = re.compile(r"physical id\s*:\s*(?P<phys_id>\d+)")
CORE_ID_M = re.compile(r"core id\s*:\s*(?P<core_id>\d+)")


def get_cpu_raw_info(cpuinfo_file):
    """Returns 'raw' cpuinfo, vendor and family of the processors."""
    with open(cpuinfo_file, 'r') as cpuif:
        lines = cpuif.readlines()
    vendor, family = get_vendor(lines)
    matchers = [PROCESSOR_M, PHYSICAL_ID_M, CORE_ID_M]
    matches = zip(*extre.all_matches(matchers, lines))
    cpu_raw_info = []
    for processor_match, physical_id_match, core_id_match in matches:
        processor = int(processor_match.group('proc'))
        physical_id = int(physical_id_match.group('phys_id'))
        core_id = int(core_id_match.group('core_id'))
        cpu_raw_info.append((physical_id, core_id, processor))
    return cpu_raw_info, vendor, family


def get_numa_info(lscpu_file):
    """Returns numa-cpus dictionary."""
    numa_r = r'''NUMA[ ]node (?P<number> \d+ )[ ]
                 CPU\(s\): \s*
                 (?P<cpus> (?: \d+ (?: - \d+ )? ,? )+ )'''  # mixed list of cpu ids and ranges (e.g. 3,5-7)
    numa_m = re.compile(numa_r, re.X)
    with open(lscpu_file, 'r') as lscpuf:
        lines = lscpuf.readlines()
    numa_info_matches = extre.matches(numa_m, lines)
    numa_to_cpus = {}
    for match in numa_info_matches:
        numa_number = int(match.group('number'))
        numa_cpus = parsers.sranges_to_list(match.group('cpus'))
        numa_to_cpus[numa_number] = numa_cpus
    return numa_to_cpus
