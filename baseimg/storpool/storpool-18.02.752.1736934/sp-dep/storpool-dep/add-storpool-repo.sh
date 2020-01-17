#!/bin/sh

set -e

install -C -o root -g root -m 644 'repo/storpool-centos.repo' /etc/yum.repos.d/
install -C -o root -g root -m 644 'repo/RPM-GPG-KEY-StorPool' /etc/pki/rpm-gpg/

rpmkeys_prog="$(type -p rpmkeys 2>/dev/null || true)"
if [ -f "$rpmkeys_prog" ] && [ -x "$rpmkeys_prog" ]; then
	"$rpmkeys_prog" --import '/etc/pki/rpm-gpg/RPM-GPG-KEY-StorPool'
fi

yum --enablerepo=storpool-contrib clean metadata
