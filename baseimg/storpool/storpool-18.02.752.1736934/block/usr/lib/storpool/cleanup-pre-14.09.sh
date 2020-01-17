#!/bin/bash
#
#-
# Copyright (c) 2013  StorPool.
# All rights reserved.
#

set -e

case "$1" in
	#cleanup old service storpool_bd ( currently named storpool_block )
	[yY][eE][sS])
		service stop storpool_bd || true
		if [ -d /etc/systemd/system ]; then
			systemctl disable storpool_bd.service || true
			rm -vf /etc/systemd/system/storpool_bd.service || true
		fi
		rm -vf /etc/{init.d,rc{,{0..6}}.d}/*storpool_bd || true
		rm -vf /usr/sbin/storpool_bd* || true
		;;
	*)
		echo "! WARNING !"
		echo " This script removes 'storpool_bd'! If you are sure pass 'yes' as parameter"
		exit 1
esac
