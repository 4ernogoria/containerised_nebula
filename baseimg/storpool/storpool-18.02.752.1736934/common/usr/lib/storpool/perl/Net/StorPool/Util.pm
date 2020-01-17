#!/usr/bin/perl
#
#-
# Copyright (c) 2016  StorPool.
# All rights reserved.
#

package Net::StorPool::Util;

use v5.010;
use strict;
use warnings;
use Config::IniFiles;

our $VERSION = "0.02";

use base qw(Exporter);

our @EXPORT_OK = qw(
	debug set_debug
	check_wait_result run_command
	detect_libc
);

our %EXPORT_TAGS = (
	debug => [qw(debug set_debug)],
);

our $debug;

sub set_debug($)
{
	$debug = $_[0];
}

sub debug($)
{
	say STDERR $_[0] if $debug;
}

sub check_wait_result($ $ $)
{
	my ($stat, $pid, $name) = @_;
	my $sig = $stat & 127;
	if ($sig != 0) {
		die "Program '$name' (pid $pid) was killed by signal $sig\n";
	} else {
		my $code = $stat >> 8;
		if ($code != 0) {
			die "Program '$name' (pid $pid) exited with non-zero status $code\n";
		}
	}
}

sub run_command(@)
{
	my (@cmd) = @_;
	my $name = $cmd[0];

	my $pid = open my $f, '-|';
	if (!defined $pid) {
		die "Could not fork for $name: $!\n";
	} elsif ($pid == 0) {
		debug "About to run '@cmd'";
		exec { $name } @cmd;
		die "Could not execute '$name': $!\n";
	}
	my @res = <$f>;
	chomp for @res;
	close $f;
	check_wait_result $?, $pid, $name;
	return @res;
}

sub detect_libc($)
{
	my ($variant) = @_;

	my ($libc_name, @libc_ver);
	if ($variant =~ /^( DEBIAN | UBUNTU )/x) {
		my @arch = run_command 'dpkg', '--print-architecture';
		if (@arch != 1) {
			die "Unexpected dpkg --print-architecture output: ".
				scalar(@arch)." lines instead of a single one\n";
		}
		$libc_name = "libc6:$arch[0]";
		@libc_ver = run_command 'dpkg-query', '-f', '${Version}\n',
			'-W', $libc_name;
	} elsif ($variant =~ /^( CENTOS )/x) {
		my @arch = run_command 'rpm', '-q', '--qf', '%{arch}\n', '-f', '/etc/redhat-release';
		{
			my %seen;
			@arch = grep { my $seen = $seen{$_}; $seen{$_}++; !$seen } @arch;
		}
		if (@arch != 1) {
			die "Unexpected rpm -q -f /etc/redhat-release output: ".
				scalar(@arch)." lines instead of a single one\n";
		}
		$libc_name = "glibc.$arch[0]";
		@libc_ver = run_command 'rpm', '--qf', '%{v}-%{r}.%{arch}\n',
			'-q', $libc_name;
	} else {
		die "Don't know how to query the libc version for variant '$variant'\n";
	}
	if (@libc_ver != 1) {
		die "Unexpected libc version query output: ".
			scalar(@libc_ver)." lines instead of a single one\n";
	}

	return (libc_name => $libc_name, libc_ver => $libc_ver[0]);
}

1;
