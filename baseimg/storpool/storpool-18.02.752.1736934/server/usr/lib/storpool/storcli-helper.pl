#!/usr/bin/perl

use 5.010;
use strict;
use warnings;

use Cwd;
use File::Spec;
use File::Temp;
use Getopt::Std;
use POSIX qw/:sys_wait_h/;

my $debug = 0;

sub find_storcli($);
sub do_stuff($ $);
sub check_wait_result($ $ $);

sub version();
sub usage($);
sub debug($);

my @tempdirs;

MAIN:
{
	my %opts;

	getopts('hp:Vv', \%opts) or usage(1);
	version() if $opts{V};
	usage(0) if $opts{h};
	exit(0) if $opts{V} || $opts{h};
	$debug = $opts{v};

	if (@ARGV != 1) {
		warn("No device name specified\n");
		usage(1);
	}
	my $dev = $ARGV[0];

	debug('Looking for the thing that leaves files lying around :)');
	my $prog = 'storcli64';
	if (defined($opts{p})) {
		my ($v, $dirs, $f) = File::Spec->splitpath($opts{p});
		if (length($dirs) &&
		    !File::Spec->file_name_is_absolute($opts{p})) {
			$prog = File::Spec->canonpath(
			    File::Spec->catfile(getcwd(), $opts{p}));
		} else {
			$prog = $opts{p};
		}
	}
	debug("Using the $prog tool");

	my $d = File::Temp->newdir();
	debug("Created a temp directory $d");

	debug('Forking...');
	my $pid = fork();
	if (!defined($pid)) {
		die("Could not fork: $!\n");
	} elsif ($pid == 0) {
		chdir($d) or die("Could not change into $d: $!\n");
		do_stuff($prog, $dev);
		exit(0);
	}
	debug("Parent $$: forked off child worker $pid");
	my $waitedpid = waitpid($pid, 0);
	my $stat = $?;
	if ($waitedpid == -1) {
		die("Parent $$: something weird happened to child $pid\n");
	} elsif ($pid != $waitedpid) {
		warn("Parent $$: waited for pid $pid, got $waitedpid instead\n");
	}
	debug("Parent $$: process $pid finished with status $stat");
	check_wait_result($stat, $pid, $0);
}

sub usage($)
{
	my ($err) = @_;
	my $s = <<EOUSAGE
Usage:	storcli-helper [-v] [-p prog] devname
	storcli-helper -V | -h

	-h	display program usage information and exit
	-p	specify the path to the storcli tool
	-V	display program version information and exit
	-v	verbose operation; display diagnostic output
EOUSAGE
	;

	if ($err) {
		die($s);
	} else {
		print "$s";
	}
}

sub version()
{
	print "storcli-helper 0.01\n";
}

sub debug($)
{
	say STDERR $_[0] if $debug;
}

sub getSys($)
{
	my ($dev) = @_;
	debug("& getSys($dev)");

	$dev =~ s/\/dev\///;
## ls -la /sys/class/block/sda /sys/class/block/sdc
#lrwxrwxrwx. 1 root root 0 Feb  9 14:40 /sys/class/block/sda -> ../../devices/pci0000:00/0000:00:03.0/0000:04:00.0/host11/target11:0:10/11:0:10:0/block/sda
#lrwxrwxrwx. 1 root root 0 Feb  9 14:40 /sys/class/block/sdc -> ../../devices/pci0000:00/0000:00:03.0/0000:04:00.0/host11/target11:2:2/11:2:2:0/block/sdc
	my $sysClass = readlink "/sys/class/block/$dev";
	debug("& getSys($dev) sysClass:$sysClass");
	my @path = split'/',$sysClass;
	my $scsi = $path[-3];
	my $pci = $path[-6];
	debug("& getSys($dev) scsi:$scsi pci:$pci");
	my ($type,$id) = $scsi =~ /^\d+:(\d+):(\d+):\d+/;
	die "Can't decode SCSI id from $scsi!($sysClass)" if !defined($type);
	my ($bus,$device,$func) = $pci =~ /^[0-9a-f]+:([0-9a-f]+):([0-9a-f]+)\.([0-9a-f]+)/i;
	die "Can't decode PCI from $pci!($sysClass)" if !defined($bus);
	$bus = hex($bus);
	$device = hex($device);
	$func = hex($func);
#	debug "($type,$id) ($bus,$device,$func)";
	return $type,$id,$bus,$device,$func;
}

sub getController($$$$$)
{
	my ($prog, $dev, $b, $d, $f) = @_;
	debug("& getController($prog,$dev,$b,$d,$f)");
	my ($ctrl,$bus,$device,$func);
	my @lines = run_storcli($prog, "/call", "show", "pci");
	foreach(@lines){
		chomp;
		if ( /^Controller\s*=\s*([a-z0-9]+)/i ){
			#Controller = 0
			$ctrl = $1;
			$bus = $device = $func = "";
			debug("& Controller: HIT->$_");
		} elsif ( /^Bus\s*Number\s+([a-z0-9]+)/i ){
			#Bus Number      1
			$bus = $1;
			debug("& PCI: HIT->$_");
		} elsif ( /^Device\s*Number\s+([a-z0-9]+)/i ){
			#Device Number   0
			$device = $1;
			debug("& PCI: HIT->$_");
		} elsif ( /^Function\s*Number\s+([a-z0-9]+)/i ){
			#Function Number 0
			$func = $1;
			debug("& PCI: HIT->$_");
			if ( $bus==$b && $device==$d && $func==$f ) {
				debug("& Controller $ctrl MATCH");
				return $ctrl;
			}
			debug("PCI(no match) bus:$bus<>$b, device:$device<>$d, func:$func<>$f");
		}
	}
	die("Can't get controller ID via '$prog /call show pci'");
}

sub printSerialModel($ $ $ $)
{
	my ($prog, $ctrl, $eid, $slot) = @_;
	my($serial, $model, $model1);
	my @lines=();

	#Drive /c0/e64/s0 Device attributes :
	#==================================
	#SN =       JP1532FR1HHAYK
	#Model Number = Hitachi HDS72105
	if ( ($eid // '') ne '' ){
		debug("& printSerialModel($prog,$ctrl,$eid,$slot)");
		@lines = run_storcli($prog, "/c$ctrl", "/e$eid", "/s$slot", "show", "all");
	} else {
		debug("& printSerialModel($prog,$ctrl,n/a,$slot)");
		@lines = run_storcli($prog, "/c$ctrl", "/s$slot", "show", "all");
	}
	foreach (@lines) {
		s/[\r\n]*$//;
		if ( /^SN\s*=\s*(.+)/ ){
			debug("& printSerialModel: HIT-SERIAL>$_");
			die("More than one 'SN'='$1' line! Previous: '$serial'\n") if defined($serial);
			$serial = $1;
		} elsif ( /^Model\sNumber\s*=\s*(.+)/ ) {
			debug("& printSerialModel: HIT-MODEL>$_");
			die("More than one 'Model Number'='$1' line! Previous: '$model'\n") if defined($model);
			$model = $1;
		}
		#---------------------------------------------------------------------------
		#EID:Slt DID State DG     Size Intf Med SED PI SeSz Model                Sp
		#---------------------------------------------------------------------------
		#8:5      11 Onln   3 2.729 TB SATA HDD N   N  512B HGST HUS724030ALA640 U
		#---------------------------------------------------------------------------
		elsif ( /\s*\d+:\d+\s+\d+\s+.+\s+\d+\w+\s+(.+)\s+\w+\s*/i) {
			debug("& printSerialModel: HIT->$_");
			die("More than one model1 '$1' line! Previous: '$model1'\n") if defined($model1);
			$model1 = $1;
		}
		if ( defined($model) && defined($serial) ) {
			die("WTF, serial $serial model $model\n") if "$serial$model" =~ /[^A-Za-z0-9.,=\/_\s+=-]/;
			$model = $model1 if ( defined($model1) && index($model1,$model) != -1 );
			$serial =~ s/\s+$//;
			$model =~ s/\s+$//;
			say "ID_SERIAL='$serial'";
			say "ID_MODEL='$model'";
			if ( $eid // '' ne '' ){
			  say "ID_ENCLOSURE='$eid'";
			} else {
			  say "ID_ENCLOSURE=''";
			}
			say "ID_SLOT='$slot'";
			say "ID_CTRL='$ctrl'";
			return;
		}
	}
}

sub type0($ $ $)
{
	my ($prog, $ctrl, $id) = @_;
	debug("& type0($prog,$ctrl,$id)");

	#--------------------------------------------------------------------------------
	#EID:Slt DID State DG       Size Intf Med SED PI SeSz Model                   Sp
	#--------------------------------------------------------------------------------
	#64:0      4 JBOD  -  464.729 GB SATA HDD N   N  512B Hitachi HDS721050CLA360 U
	#--------------------------------------------------------------------------------
	my ($eid, $slot);
	my @lines = run_storcli($prog, "/c$ctrl", "show");
	foreach (@lines) {
		s/[\r\n]*$//;
		if ( /^\s*(\d+):(\d+)\s+\Q$id\E\s+JBOD/ ) {
			debug("& type0: HIT->$_");
			die("More than one eid=$1, slot=$2 line! Previous: eid=$eid, slot=$slot\n") if defined($eid);
			$eid = $1;
			$slot = $2;
		}
	}
	die "ctrl:$ctrl, id:$id, EID not found!" if !defined($eid);
	die "ctrl:$ctrl, id:$id, Slot not found!" if !defined($slot);
	printSerialModel($prog, $ctrl, $eid, $slot);
}

sub type2($ $ $)
{
	my ($prog, $ctrl, $id) = @_;
	debug("& type2($prog,$ctrl,$id)");

	#---------------------------------------------------------
	#DG/VD TYPE  State Access Consist Cache sCC     Size Name
	#---------------------------------------------------------
	#9/9   RAID0 Optl  RW     Yes     NRWBD -   2.729 TB VD_9
	#---------------------------------------------------------
	my $dg;
	my @lines = run_storcli($prog, "/c$ctrl", "/v$id", "show");
	foreach (@lines) {
		s/[\r\n]*$//;
		if( /^\s*(\d+)\/\Q$id\E\s+RAID0/ ) {
			debug("& type2: HIT1->$_");
			die("More than one 'DG'='$1' line! Previous: '$dg'\n") if defined($dg);
			$dg = $1;
		}
	}
	die "ctrl:$ctrl, id:$id, DG/$id not found!" if !defined($dg);
	#------------------------------------------------------------------------
	#DG Arr Row EID:Slot DID Type  State BT     Size PDC  PI SED DS3  FSpace
	#------------------------------------------------------------------------
	# 9 -   -   -        -   RAID0 Optl  N  2.729 TB enbl N  N   dflt N
	# 9 0   -   -        -   RAID0 Optl  N  2.729 TB enbl N  N   dflt N
	# 9 0   0   8:11     19  DRIVE Onln  N  2.729 TB enbl N  N   dflt -
	#------------------------------------------------------------------------
	#>or without EID:
	#---------------------------------------------------------------------------
	#DG Arr Row EID:Slot DID Type  State BT     Size PDC  PI SED DS3  FSpace TR
	#---------------------------------------------------------------------------
	# 0 -   -   -        -   RAID0 Optl  N  1.818 TB dsbl N  N   dflt N      N
	# 0 0   -   -        -   RAID0 Optl  N  1.818 TB dsbl N  N   dflt N      N
	# 0 0   0    :2      26  DRIVE Onln  Y  1.818 TB dsbl N  N   dflt -      N
	#---------------------------------------------------------------------------
	my($eid, $slot);
	@lines = run_storcli($prog, "/c$ctrl", "/d$dg", "show");
	foreach (@lines) {
		s/[\r\n]*$//;
		if ( /^\s*\Q$dg\E\s+\d+\s+\d+\s+(\d+)\:(\d+)\s+\d+\s+DRIVE/ ) {
			debug("& type2: HIT2->".$_);
			die("More than one eid=$1, slot=$2 line! Previous: eid=$eid, slot=$slot\n") if defined($eid);
			$eid = $1;
			$slot = $2;
		}
		elsif ( /^\s*\Q$dg\E\s+\d+\s+\d+\s+\:(\d+)\s+\d+\s+DRIVE/ ) {
			debug("& type2: HIT2(noEID)->".$_);
			die("More than one eid=$1, slot=$2 line! Previous: eid=$eid, slot=$slot\n") if defined($eid);
			$slot = $1;
		}
	}

	printSerialModel($prog, $ctrl, $eid, $slot);
}

sub do_stuff($ $)
{
	my ($prog, $dev) = @_;
	debug("& do_stuff($prog,$dev)");

	my ($type,$id,$bus,$device,$func) = getSys($dev);
	my $ctrl = getController($prog,$dev,$bus,$device,$func);

	if ( $type == 0 ) {
		type0($prog, $ctrl, $id);
	} elsif ( $type == 2 ) {
		type2($prog, $ctrl, $id);
		say "ID_VDID='$id'";
	} else {
		die("Unknown type $type!\n");
	}
}


sub run_storcli($ @)
{
	my ($prog, @args) = @_;

	my $f;
	debug("# $prog @args");
	my $pid = open($f, '-|', $prog, @args) or
	    die("Could not run $prog: $!\n");
	my @lines = <$f>;
	if (!close($f)) {
		my $stat = $?;
		check_wait_result($stat, $pid, $prog);
	}
	return @lines;
}


sub check_wait_result($ $ $)
{
	my ($stat, $pid, $name) = @_;

	if (WIFEXITED($stat)) {
		if (WEXITSTATUS($stat) != 0) {
			die("Program '$name' (pid $pid) exited with non-zero status ".WEXITSTATUS($stat)."\n");
		}
	} elsif (WIFSIGNALED($stat)) {
		die("Program '$name' (pid $pid) was killed by signal ".WTERMSIG($stat)."\n");
	} elsif (WIFSTOPPED($stat)) {
		die("Program '$name' (pid $pid) was stopped by signal ".WSTOPSIG($stat)."\n");
	} else {
		die("Program '$name' (pid $pid) neither exited nor was killed or stopped; what does wait(2) status $stat mean?!\n");
	}
}
