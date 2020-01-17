#!/usr/bin/perl
#
#-
# Copyright (c) 2015  StorPool.
# All rights reserved.
#

use 5.010;
use strict;
use warnings;

use Cwd;
use File::Spec;
use File::Temp;
use Getopt::Std;
use POSIX qw/:sys_wait_h/;

my $debug = 0;

sub do_stuff($ $);
sub check_wait_result($ $ $);

sub version();
sub usage($);
sub debug($);

my @tempdirs;

#/opt/hp/hpssacli/bld/hpssacli controller all show
#
#Smart HBA H240ar in Slot 0 (Embedded) (RAID Mode)  (sn: PDNLN0BRH7Q0BI)
#


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
	
	my $prog = 'hpssacli';
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

	debug("Forking...");
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
Usage:	hpssacli-helper.pl [-v] [-p prog] devname
	hpssacli-helper.pl -V | -h

	-h	display program usage information and exit
	-p	specify the path to the hpssacli tool
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
	print "hpssacli-helper.pl 1.00\n";
}

sub debug($)
{
	say STDERR $_[0] if $debug;
}

sub getControllers($)
{
	my ($prog) = @_;
	my $ret = {};
	debug("& getControllers($prog)");
	my @lines = run_hpssacli($prog, qw/controller all show detail/);
	my $slot = -1;
	my $serial = '';
	foreach(@lines) {
		s/[\r\n]*$//;
		if (/\s*Slot:\s+(\d+)$/) {
			$slot = $1;
		}
		if (/\s*Serial\s+Number:\s+(.*)/) {
			$serial = $1;
		}
		if ( $serial && $slot > -1 && !defined($ret->{$slot})) {
			debug(">> slot=$slot serial=$serial");
			$ret->{$slot} = {'slot' => $slot, 'serial' => $serial};
		}
	}
	return $ret;
}

sub getLogicalDrive($ $ $)
{
	my ($prog, $slot, $dev) = @_;
	my $ret = {};
	debug("& getLogicalDrive($prog, $slot, $dev)");
	my @lines = run_hpssacli($prog, "controller", "slot=$slot", qw/logicaldrive all show detail/);
	my $arr = '';
	my $status = '';
	my $diskName = '';
	foreach(@lines) {
		s/[\r\n]*$//;
		if (/\s*array\s+([\w\d]+)$/i) {
			$arr = $1;
			$diskName = '';
			$status = '';
		}
		if (/\s*Disk\s+Name:\s+([\/\w\d]+)/i) {
			$diskName = $1;
		}
		if (/\s*Status:\s+(.*)/) {
			$status = $1;
		}
		if ( $arr && $diskName && $status) {
			if ( $diskName eq $dev ){
				$ret = {'array' => $arr, 'diskName' => $diskName, 'status'=>$status};
				last;
			}
			$diskName = '';
		}
	}
	return $ret;
}


sub getPhysicalDrive($ $ $)
{
	my ($prog, $slot, $logarr) = @_;
	my $ret = {};
	debug("& getPhysicalDrive($prog, $slot, $logarr)");
	my @lines = run_hpssacli($prog, "controller", "slot=$slot", qw/physicaldrive all show detail/);
	my $arr = '';
	my $serial = '';
	my $model = '';
	foreach(@lines) {
		s/[\r\n]*$//;
		if (/\s*array\s+([\w\d]+)$/i) {
			$arr = $1;
			$serial = '';
			$model = '';
		}
		if (/^\s*Serial\s+Number:\s+(.*)/i) {
			$serial = $1;
		}
		if (/^\s*Model:\s+(.*)/i) {
			$model = $1;
		}
		if ( $arr eq $logarr && $serial && $model) {
			debug(">> arr=$arr, serial=[$serial], model=[$model]");
			$ret = {'array' => $arr, 'serial' => $serial, 'model' => $model};
			last;
		}
	}
	return $ret;

}

sub do_stuff($ $)
{
	my ($prog, $dev) = @_;
	debug("& do_stuff($prog,$dev)");
	
	my $controllers = getControllers($prog);
	foreach my $slot (sort{$a<=>$b} keys %{$controllers}){
		debug("& do_stuff: slot:$slot");
		my $logicals = getLogicalDrive($prog, $slot, $dev);
		if( defined($logicals->{'array'}) ){
			my $physicals = getPhysicalDrive($prog, $slot, $logicals->{'array'});
			if ( defined($physicals->{'serial'}) ){
				say "ID_SERIAL='".$physicals->{'serial'}."'";
				say "ID_MODEL='".$physicals->{'model'}."'";
				last;
			}
		}
	}
}

sub run_hpssacli($ @)
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
