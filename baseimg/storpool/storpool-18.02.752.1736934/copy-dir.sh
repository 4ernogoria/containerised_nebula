#!/bin/sh
#
# Copyright (c) 2014 - 2016  Peter Pentchev
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

set -e

# OK, so this script contains a couple of GNUisms:
# - chown --reference
# - chmod --reference
# - tar --exclude=... --no-overwrite-dir

version()
{
	echo 'copy-dir 0.2.1'
}

usage()
{
	cat <<EOUSAGE
Usage:	copy-dir [-INv] [-x pattern] filename...
	copy-dir -V | -h

	-h	display program usage information and exit
	-I	do not error out on immutable destination files or directories
	-N	no operation mode; display what would have been done
	-V	display program version information and exit
	-v	verbose operation; display diagnostic output
	-x	exclude files matching the specified pattern; may be used
		more than once.  The pattern is passed to GNU tar's
		--exclude option.
EOUSAGE
}

have_program()
{
	local prog ppath
	
	prog="$1"

	if [ -n "$BASH_VERSION" ]; then
		ppath=`type -p "$prog" 2>/dev/null`
	elif [ -n "$ZSH_VERSION" ]; then
		ppath=`whence -p "$prog" 2>/dev/null`
	else
		ppath=`which "$prog" 2>/dev/null`
	fi

	if [ -n "$ppath" ] && [ -f "$ppath" ] && [ -x "$ppath" ]; then
		return 0
	else
		return 1
	fi
}

unset excl hflag skip_immutable noop Vflag v

while getopts 'hINVvx:' o; do
	case "$o" in
		h)
			hflag=1
			;;

		I)
			skip_immutable=1
			;;

		N)
			noop='echo'
			;;

		V)
			Vflag=1
			;;

		v)
			v='-v'
			;;

		x)
			excl="$excl --exclude=$OPTARG"
			;;

		*)
			usage 1>&2
			exit 1
			;;
	esac
done
# If -V and/or -h is specified, print the request info and exit.
[ -z "$Vflag" ] || version
[ -z "$hflag" ] || usage
[ -z "$Vflag$hflag" ] || exit 0

# Skip to the positional arguments.
shift `expr "$OPTIND" - 1`
if [ "$#" -ne 2 ]; then
	usage 1>&2
	exit 1
fi

srcdir="$1"
dstdir="$2"

if [ ! -d "$dstdir" ]; then
	$noop mkdir -- "$dstdir"
	$noop chown --reference="$srcdir" -- "$dstdir"
	$noop chmod --reference="$srcdir" -- "$dstdir"
fi

[ -z "$v" ] || echo "Copying $srcdir to $dstdir"

if [ -n "$skip_immutable" ]; then
	if ! have_program lsattr; then
		echo 'Cannot skip immutable files (-I) without lsattr' 1>&2
		exit 1
	fi

	tempf=`mktemp copy-dir-immutable-check.lst.XXXXXX`
	trap "rm -f '$tempf'" HUP INT TERM QUIT EXIT

	(
		cd -- "$srcdir" && tar -cpf - $excl ./
	) | tar -tf - > "$tempf"
	
	while read fname; do
		fname="${fname%/}"
		d="$dstdir/$fname"
		if [ -e "$d" ] && [ ! -h "$d" ] && lsattr -d -- "$d" | egrep -qe '^[^[:space:]]*i'; then
			excl="$excl --exclude=$fname"
		fi
	done < "$tempf"
fi

[ -z "$v" ] || echo "Exclude specification: ${excl:-(none)}"

# Keep this in sync with the actual command several lines down
if [ -n "$noop" ]; then
	echo "cd -- '$srcdir' && tar -cpf - $excl ./"
fi

(
	cd -- "$srcdir" && tar -cpf - $excl ./
) | (
	if [ -n "$noop" ]; then
		echo "cd -- '$dstdir' && tar -xpf - --no-overwrite-dir $v"
		tar -tf -
	else
		cd -- "$dstdir" && tar -xpf - --no-overwrite-dir $v
	fi
)
