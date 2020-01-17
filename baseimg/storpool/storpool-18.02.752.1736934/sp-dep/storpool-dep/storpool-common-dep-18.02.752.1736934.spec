Name:		storpool-common-dep-18.02.752.1736934
Version:	1
Release:	1%{?dist}
Summary:	Ensure the packages required for the StorPool installation are available
BuildArch:	noarch
Requires:	kernel-tools, libcgroup-tools, perl-autodie, perl-File-Path, perl-Sys-Syslog, procps-ng, python, jq, kexec-tools, logrotate, numactl, perl, perl-BSD-Resource, perl-Config-IniFiles, perl-Data-Dump, perl-JSON-XS, perl-Time-HiRes, pexpect, psmisc, python-jinja2, PyYAML, rsyslog, screen, storpool-config-dep-18.02.752.1736934, storpool-precheck-dep-18.02.752.1736934, sysstat, tcpdump, tmux, tuned, util-linux, vim-enhanced

Group:		Applications/System
License:	Public
URL:		https://storpool.com/


%description

StorPool is distributed data storage software running on standard x86 servers.
StorPool aggregates the performance and capacity of all drives into a shared
pool of storage distributed among the servers.  Within this storage pool the
user creates thin-provisioned volumes that are exposed to the clients as block
devices.  StorPool consists of two parts wrapped in one package - a server and
a client.  The StorPool server allows a hypervisor to act as a storage node,
while the StorPool client allows a hypervisor node to access the storage pool
and act as a compute node.

This package makes sure that the OS packages needed for the StorPool
installation are installed beforehand.

%files
