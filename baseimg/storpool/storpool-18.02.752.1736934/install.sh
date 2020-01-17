#!/bin/sh
#
#-
# Copyright (c) 2013 - 2018  StorPool.
# All rights reserved.
#

set -e

re_val_username='[a-zA-Z0-9_.][a-zA-Z0-9_.]*$'

def_syncusername='storpool'

usage() {
	cat <<EOUSAGE
Usage:	install.sh [-qNS] [-k kernelname] [-u syncusername] [-x] [module...]
	install.sh --hugepages
	install.sh -l
	install.sh -h

	-h	display program usage information and exit
	-k	specify a kernel version different from the running one as
		the one required for kernel modules installation; the modules
		will still be installed for all available versions
		(default: the output of "uname -r")
	-N	no operation mode; display what would have been done
	-l	list the available installation modules
	-q	quiet mode; only display a success message
	-S	do not run "sync" at the end of the installation
	-u	specify the username for the repsync user account (default: SP_CRASH_USER or "$def_syncusername")
	-x	exclude the specified modules from the default list

	--hugepages				only run storpool_hugepages as a pre-installation check
	--skip-os-dep-install	do not install the required OS packages (use with caution!)
EOUSAGE
}

list_modules() {
	echo "Modules available for installation: $igroup_all"
	echo "Modules installed by default: $igroup_default"
	echo "Groups that may be specified:"
	local g mm maxlen=0
	for g in $install_groups; do
		local len=`echo "$g" | wc -c`
		# Actually $len is +1 since wc(1) counts the newline, too.
		if [ "$len" -gt "$maxlen" ]; then
			maxlen="$len"
		fi
	done
	for g in $install_groups; do
		eval "mm=\"\$igroup_$g\""
		printf -- '- @%-'"$maxlen"'s  %s\n' "$g" "$mm"
	done
}

filter_install_groups(){
	local g
	for g in $install_groups; do
		local m mm mmnew
		eval "mm=\"\$igroup_$g\""
		mmnew=''
		for m in $mm; do
			if [ -d "$m" ]; then
				mmnew="$mmnew $m"
			fi
		done
		mmnew="${mmnew# }"
		eval "igroup_$g=\"\$mmnew\""
	done
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

get_dist_config_dir() {
	local dirs='config common'
	local testf='usr/sbin/storpool_confget'
	local d

	for d in $dirs; do
		if [ -f "$d/$testf" ]; then
			echo "$d"
			return
		fi
	done
	lerror "$testf could not be found in any of the '$dirs' installation modules"
	exit 1
}

get_dist_conffile() {
	local d=`get_dist_config_dir`
	[ -n "$d" ] || exit 1
	local f="$d/$1"

	if [ ! -f "$f" ]; then
		lerror "$f does not exist, distribution incomplete"
		exit 1
	fi
	echo "$f"
}

get_dist_spconfget() {
	get_dist_conffile 'usr/sbin/storpool_confget'
}

get_dist_spconfshow() {
	get_dist_conffile 'usr/sbin/storpool_confshow'
}

get_defconf() {
	local fn='usr/lib/storpool/storpool-defaults.conf'

	if [ -f "/$fn" ]; then
		echo "/$fn"
	else
		get_dist_conffile "$fn"
	fi
}

spconf='/etc/storpool.conf'
repuserconf='/etc/storpool.conf.d/repsync-username.conf'

# Try to obtain the current value of SP_CRASH_USER from
# the StorPool config files.
# The single argument is a string consisting of zero or more of
# the following flags:
# - 's': use storpool_confshow for a full check
# - 'c': check just /etc/storpool.conf using confget
# - 'r': check just repsync-username.conf using confget
# If more than one flag is specified, the checks are performed in
# the 's', 'c', 'r' order; the first one that produces a non-empty
# string as a result completes the search.
#
get_conf_syncusername() {
	local mode="$1"
	local u

	if expr "x$mode" : 'x.*[^rsc]' > /dev/null; then
		lerror "Internal error: get_conf_syncusername() invoked with an invalid mode string '$mode'"
		exit 1
	fi

	case "$mode" in
		*s*)
			if [ -f "$spconf" ]; then
				# /etc/storpool.conf exists; try a full-blown storpool_confshow
				local spconfget=`get_dist_spconfget`
				local spconfshow=`get_dist_spconfshow`
				local defconf=`get_defconf`
				if ! [ -n "$spconfget" ] && [ -n "$spconfshow" ] && [ -n "$defconf" ]; then
					exit 1
				fi

				u=`"$spconfshow" -c "$spconfget" -D "$defconf" -n SP_CRASH_USER`
				if [ -n "$u" ]; then
					echo "$u"
					return
				fi
			fi
			;;
	esac

	case "$mode" in
		*r*)
			if [ -f "$repuserconf" ]; then
				# Our autogenerated SP_CRASH_USER file exists; try a simple confget
				u=`confget -f "$repuserconf" SP_CRASH_USER`
				if [ -n "$u" ]; then
					echo "$u"
					return
				fi
			fi
			;;
	esac

	case "$mode" in
		*c*)
			if [ -f "$spconf" ]; then
				# /etc/storpool.conf exists; try confget with the default
				# section first, with our hostname afterwards.
				u=`confget -f "$spconf" -O -s "$(hostname)" SP_CRASH_USER`
				if [ -n "$u" ]; then
					echo "$u"
					return
				fi
			fi
			;;
	esac

	# If there's no configuration, wisely remain silent.
}

get_reportdir() {
	if [ -f "$spconf" ]; then
		local spconfget=`get_dist_spconfget`
		local spconfshow=`get_dist_spconfshow`
		local defconf=`get_defconf`
		if ! [ -n "$spconfget" ] && [ -n "$spconfshow" ] && [ -n "$defconf" ]; then
			exit 1
		fi

		local dir=`"$spconfshow" -c "$spconfget" -D "$defconf" -n SP_REPORTDIR`
		if [ -n "$dir" ]; then
			echo "$dir"
			return
		fi
	fi

	echo '/var/spool/storpool'
}

get_workdir() {
	if [ -f "$spconf" ]; then
		local spconfget=`get_dist_spconfget`
		local spconfshow=`get_dist_spconfshow`
		local defconf=`get_defconf`
		if [ -z "$spconfget" ] || [ -z "$spconfshow" ] || [ -z "$defconf" ]; then
			exit 1
		fi

		local dir=`"$spconfshow" -c "$spconfget" -D "$defconf" -n SP_WORKDIR`
		if [ -n "$dir" ]; then
			echo "$dir"
			return
		fi
	fi

	echo '/var/run/storpool'
}

lecho()
{
	[ -n "$qflag" ] || echo "$@"
	if [ -n "$install_log" ]; then
		echo "$@" >> "$install_log"
	fi
}

ldebug()
{
	if [ -n "$install_log" ]; then
		echo "$@" >> "$install_log"
	fi
}

lerror()
{
	echo "$@" 1>&2
	if [ -n "$install_log" ]; then
		echo "$@" >> "$install_log"
	fi
}

copydir()
{
	if [ -n "$install_log" ]; then
		echo "Copying a directory: $@" >> "$install_log"
		$copydir "$@" >> "$install_log"
	else
		$copydir "$@"
	fi
}

add_grub_parameters()
{
	local add_libata add_swapaccount add_disablefb
	for m in $modules; do
		case "$m" in
			beacon|block|iscsi|mgmt)
				add_swapaccount=1
				add_disablefb=1
				;;

			server)
				add_swapaccount=1
				add_libata=1
				add_disablefb=1
				;;

			*)
				;;
		esac
	done

	local add_params params_line

	if [ -n "$add_libata" ]; then
		add_params="$add_params libata.fua=1"
	fi
	if [ -n "$add_swapaccount" ]; then
		add_params="$add_params swapaccount=1"
	fi
	if [ -n "$add_disablefb" ]; then
		# note that there are too many ways for the framebuffer to be started, these are to be on the safe side.
		add_params="$add_params vga=normal nofb nomodeset video=vesafb:off i915.modeset=0"
	fi

	if [ -z "$add_params" ]; then
		return
	fi
	add_params="${add_params# }"

	local fname='/etc/default/grub'

	if [ ! -f "$fname" ]; then
		if have_program grubby; then
			# needed for centos 6
			for p in $add_params; do
				$noop grubby --update-kernel=ALL --args="$p"
			done
		else
			lerror "Could not find $fname and no grubby; not examining the kernel command line"
		fi
		return
	fi

        tempf=`mktemp $(dirname -- "$fname")/storpool-default-grub.XXXXXX`
        trap "rm -f -- '$tempf'" HUP INT TERM QUIT EXIT

	# create temp file not to screw up with the original
	sed -e '/# AUTOGENERATED BY StorPool/,$d' -- $fname  > $tempf

	local cmd="$(. "$tempf"; printf '%s %s' "$GRUB_CMDLINE_LINUX" "$GRUB_CMDLINE_LINUX_DEFAULT")"
	echo "Examining the kernel command line: $cmd" >> "$install_log"
	echo "Checking for $add_params" >> "$install_log"

	local add
	for e in $add_params; do
		if [ "${cmd#*$e}" = "$cmd" ]; then
			add="$add $e"
		fi
	done


	if [ -z "$add" ]; then
		echo "It seems to contain all the required parameters" >> "$install_log"
	else
		add="${add# }"
		lecho "Adding parameters to the kernel command line: $add"
		params_line='GRUB_CMDLINE_LINUX="$GRUB_CMDLINE_LINUX '"$add"'"'
	fi

	if [ -z "$noop" ] && ! [ -z "$params_line" ] ; then
		cat >> "$tempf" <<EOFGRUB

# AUTOGENERATED BY StorPool, DO NOT EDIT BELOW THIS LINE
# Generated on $(env LANG=C date -R) by $(readlink -e -- "$0")
$params_line
EOFGRUB
	fi
	mv -- "$tempf" "$fname"
	trap '' HUP INT TERM QUIT EXIT

}

spdep_install()
{
	local modules="$1"
	local spdep='sp-dep/storpool-dep'

	local spdep_modules="install $modules"
	local mcheck
	for mcheck in $spdep_modules; do
		local fname="$spdep/package-$mcheck-dep.txt"
		if [ ! -f "$fname" ]; then
			lerror "The $spdep directory does not exist or there is no $fname file!"
			lerror 'Is the StorPool distribution archive complete?'
			exit 1
		fi
	done

	if ! (set -e; cd -- "$spdep"; ./install-packages.sh $spdep_modules >> "$install_log" 2>&1); then
		lerror 'Could not install at least some of the OS dependencies!'
		lerror "Please see the $install_log file for details about the errors encountered."
		exit 1
	fi
}

run_helper()
{
	config/usr/lib/storpool/install_helper ${noop+-N} ${qflag+-q} -m "$modules" "$@"
}

do_check_prelinked()
{
	local check_prelinked bad m mbin mbasebin mbase

	check_prelinked='common/usr/lib/storpool/check_prelinked'
	if [ ! -x "$check_prelinked" ]; then
		return
	fi
	
	unset bad
	for m in $modules; do
		if [ ! -d "$m/usr/sbin" ]; then
			continue
		fi
		for mbin in $(find -- "$m/usr/sbin/" -type f -name 'storpool_*.bin'); do
			mbasebin="$(basename -- "$mbin")"
			mbase="${mbasebin%.bin}"
			if [ -x "/usr/sbin/$mbase" ] && [ -f "/var/run/$mbase.pid" ]; then
				if ! "$check_prelinked" "$mbase" "/var/run/$mbase.pid"; then
					bad=1
				fi
			fi
		done
	done
	if [ -n "$bad" ]; then
		lerror 'Prelinked service executable files found, aborting'
		exit 1
	fi
}

determine_kernel_versions() {
	local kver_all="$(find /lib/modules/ -mindepth 1 -maxdepth 1 -type d -printf '%P ')"
	ldebug "Kernel versions installed: $kver_all"
	ldebug "Kernel version requested: $kernelname"
	if [ -z "$kver_all" ]; then
		lerror 'Could not find any installed kernels at all'
		exit 1
	fi

	# Figure out what's the latest kernel version that we have modules for
	# with the same major version as the requested one.
	kernel_versions="$kver_all"
	local req_major="${kernelname%%.*}"
	local req_regexp="^$req_major\\."
	local filter='\.'
	case "$kernelname" in
		*.el*)
			filter='\.el'
			;;
		
		*.vz*)
			filter='\.vz'
			;;
	esac
	local latest="$(egrep -e "$req_regexp.*$filter" kernel-versions.txt | tail -n1)"
	ldebug "Kernel major version '$req_major' regexp '$req_regexp' latest '$latest'"
	if [ -z "$latest" ]; then
		lerror "No StorPool kernel modules built for the $req_major.* series, see the kernel-versions.txt file for a list"
		exit 1
	elif ! echo "$kernel_versions" | tr ' ' "\n" | fgrep -qxe "$latest"; then
		kernel_versions="$kernel_versions $latest"
		ldebug "Adding '$latest' to the list of all kernel versions, now '$kernel_versions'"
	fi

	# Now figure out which of these we have modules for.
	local found_modules='' m=''
	for m in $modules; do
		if [ ! -d "$m/lib/modules" ]; then
			continue
		elif [ ! -d "$m/lib/modules/$kernelname" ]; then
			local available="$(find -- "$m/lib/modules/" -mindepth 1 -maxdepth 1 -type d | xargs -rn1 basename | env LANG=C sort -V | xargs -r)"
			if [ -n "$available" ]; then
				lerror "Kernel name mismatch in the '$m' module: expected '$kernelname', found $available"
			else
				lerror "Kernel name mismatch in the '$m' module: expected '$kernelname', '$m/lib/modules/' exists, but it does not contain any kernel module directories"
			fi
			exit 1
		fi
		found_modules=1

		local kver_tmp=''
		for kver in $kernel_versions; do
			if [ -d "$m/lib/modules/$kver" ]; then
				kver_tmp="$kver_tmp $kver"
			fi
		done
		if [ -z "$kver_tmp" ]; then
			lerror 'Could not find any modules to install for the installed kernels'
			exit 1
		fi
		kernel_versions="$kver_tmp"

		# Let's hope that all kernel modules are built for all kernel versions
		# so that it's enough to check just one.
		break
	done
	if [ -z "$found_modules" ]; then
		kernel_versions=''
	else
		lecho "Kernel versions to install for: $kernel_versions"
	fi
}

distdir=`dirname "$0"`
if [ -z "$distdir" ]; then
	echo "Warning: could not determine the path to install.sh from '$0', proceeding from the current directory '`pwd`'" 1>&2
else
	cd "$distdir"
fi

cp='cp -fv --remove-destination'

dist_modules='beacon bindings-py block bridge cli config common debug iscsi kubernetes mgmt multiserver repsync server update'
all_modules=''
for m in $dist_modules; do
	if [ -d "$m" ]; then
		all_modules="$all_modules $m"
	fi
done
all_modules="${all_modules# }"
igroup_all="$all_modules"

igroup_default='beacon bindings-py block cli config common debug mgmt repsync server update'

_igroup_common='bindings-py config common'

igroup_bindings="$_igroup_common"

igroup_block="$_igroup_common beacon block repsync update"
igroup_block_server="$igroup_block server"
igroup_block_server_mgmt="$igroup_block_server bindings-py cli mgmt"

igroup_cli="config cli"

igroup_iscsi="$_igroup_common beacon iscsi repsync update"
igroup_iscsi_server="$igroup_iscsi server"
igroup_iscsi_server_mgmt="$igroup_iscsi_server bindings-py cli mgmt"

install_groups='all bindings block block_server block_server_mgmt cli default iscsi iscsi_server iscsi_server_mgmt'
filter_install_groups

unset hugepages_reserve hflag lflag noop nopkg qflag syncusername nosync xflag
kernelname="`uname -r`"

while getopts 'hk:NlqSu:x-:' o; do
	case "$o" in
		h)
			hflag=1
			;;

		k)
			kernelname="$OPTARG"
			;;

		l)
			lflag=1
			;;

		N)
			noop='echo'
			;;

		q)
			qflag=1
			;;

		S)
			nosync=1
			;;
			
		u)
			if expr "x$OPTARG" : "x$re_val_username" > /dev/null; then
				syncusername="$OPTARG"
			else
				echo 'Invalid username specified' 1>&2
				exit 1
			fi
			;;

		x)
			xflag=1
			;;

		-)
			if [ "$OPTARG" = 'skip-os-dep-install' ]; then
				nopkg=1
			elif [ "$OPTARG" = 'hugepages' ]; then
				hugepages_reserve=1
			else
				echo "Invalid long option '$OPTARG' specified" 1>&2
				usage 1>&2
				exit 1
			fi
			;;

		*)
			usage 1>&2
			exit 1
			;;
	esac
done

[ -z "$hflag" ] || usage
[ -z "$lflag" ] || list_modules
[ -z "$hflag$lflag" ] || exit 0

shift `expr "$OPTIND" - 1`

idir="$PWD"
copydir="$idir/copy-dir.sh -v ${noop+-N}"
if [ -z "$noop" ]; then
	finddelete='-delete'
else
	finddelete=''
fi

if [ -n "$hugepages_reserve" ]; then
	lecho 'The --hugepages option was specified, using "config beacon" as the list of modules'
	set -- config beacon
fi

if [ "$#" -eq 0 ]; then
	lerror 'No modules to install'
	usage 1>&2
	exit 1
fi

if [ -n "$xflag" ]; then
	modules="$igroup_default"
else
	modules=''
fi

m_name_re='[a-z][a-z0-9_-]*'
m_group_name_re='[a-z][a-z0-9_]*'
while [ "$#" -gt 0 ]; do
	mm="$1"
	shift
	mm_name="${mm#@}"
	if [ "$mm_name" != "$mm" ]; then
		if ! expr "x$mm_name" : "x$m_group_name_re\$" > /dev/null; then
			lerror "Invalid module group name '$mm_name'"
			exit 1
		elif ! echo "$install_groups" | tr ' ' "\n" | fgrep -qxe "$mm_name"; then
			lerror "Unknown module group '$mm_name'"
			exit 1
		fi
		eval "mm=\"\$igroup_${mm_name}\""
		if [ -z "$mm" ]; then
			lerror "Internal error: empty module group '$mm_name'"
			exit 1
		fi
	elif ! expr "x$mm" : "x$m_name_re\$" > /dev/null; then
		lerror "Invalid module name '$mm'"
		exit 1
	fi
	for m in $mm; do
		if ! expr "x$m" : "x$m_name_re\$" > /dev/null; then
			lerror "Invalid module name '$m'"
			exit 1
		elif ! echo "$all_modules" | tr ' ' "\n" | fgrep -qxe "$m"; then
			lerror "Unavailable module $m, use -l to list the available ones"
			exit 1
		fi

		if [ -n "$xflag" ]; then
			modules=`echo "$modules" | tr ' ' "\n" | fgrep -vxe "$m" | xargs echo`
		else
			modules="$modules $m"
		fi
	done
done

modules="${modules# }"

if [ -z "$modules" ]; then
	lerror 'No modules to install'
	exit 1
fi
modules=`echo "$modules" | tr ' ' "\n" | sort -u | xargs`

install_log="$(pwd)/install.log"

if ! find . -mindepth 1 -maxdepth 1 -type f -name install.sh -user root | fgrep -qe install.sh; then
	lerror 'The install.sh file does not seem to be owned by root!'
	lerror 'Please extract the StorPool distribution tarball as root and try again.'
	exit 1
fi

do_check_prelinked

lecho "StorPool installation started at `env LANG=C date -R`"
lecho "Please see the $install_log file for detailed information"
lecho "Modules to install: $modules"

no_kernel_modules='1'
for m in $modules; do
	if [ -d "$m/lib/modules" ]; then
		unset no_kernel_modules
		break
	fi
done
if [ -n "$no_kernel_modules$hugepages_reserve" ]; then
	kernel_versions=''
else
	determine_kernel_versions
fi

if [ -z "$nopkg" ]; then
	lecho "Installing the required OS packages..."
	spdep_install "$modules"
else
	lecho 'SKIPPING the installation of the required OS packages!'
	if [ ! -f /usr/bin/confget ] || [ ! -x /usr/bin/confget ]; then
		lecho 'confget not found, attempting to install the configuration parser prerequisites'
		spdep_install config
	fi
fi

if [ -n "$hugepages_reserve" ]; then
	if [ ! -d 'config' ] || [ ! -d 'beacon' ]; then
		lerror 'The -H option may only be used if the installation package contains both the config and beacon modules'
		exit 1
	fi
	lecho 'Attempting to reserve hugepages for the StorPool services'
	if ! PYTHONPATH="$(pwd)/config/usr/lib/storpool/python" ./beacon/usr/sbin/storpool_hugepages -esv; then
		lerror 'The storpool_hugepages tool failed'
		exit 1
	fi
	lecho 'Successfully reserved hugepages'
	exit
fi

run_helper check

run_helper preinst

if echo "$modules" | fgrep -qwe 'repsync'; then
	# Check if storpool.conf contains a different value for SP_CRASH_USER
	confusername=`get_conf_syncusername c`
	if [ -n "$syncusername" ] && [ -n "$confusername" ] && [ "$syncusername" != "$confusername" ]; then
		lerror "A different value for SP_CRASH_USER is set in $spconf: '$confusername' instead of '$syncusername'.  This will only lead to problems; please unset it!"
		exit 1
	fi

	if [ -n "$qflag" ]; then
		exec 9>&1 > /dev/null
	fi

	# Remove the crashsync part from the storpool account' 1>&2
	if getent passwd storpool > /dev/null; then
		lecho 'Checking for any crashsync commands in the crontab of the storpool account'
		tempf=`mktemp storpool-install-crontab.txt.XXXXXX`
		trap "rm -f -- '$tempf'" HUP INT TERM QUIT EXIT

		if crontab -l -u storpool > "$tempf" 2>/dev/null && fgrep -qe 'crashsync' -- "$tempf"; then
			lecho 'Removing the crashsync commands from the crontab of the storpool account'
			fgrep -ve 'crashsync' -- "$tempf" | crontab -u storpool -
		else
			lecho 'No crashsync commands found in the crontab of the storpool account'
		fi

		rm -f -- "$tempf"
		trap '' HUP INT TERM QUIT EXIT
	fi

	if [ -z "$syncusername" ]; then
		if [ -n "$confusername" ]; then
			syncusername="$confusername"
			lecho "- using $syncusername"
		fi
	fi
	if [ -z "$syncusername" ]; then
		lecho "Checking for SP_CRASH_USER in $spconf and $repuserconf"
		syncusername=`get_conf_syncusername src`
		if [ -n "$syncusername" ]; then
			lecho "- found $syncusername"
		fi
	fi
	if [ -z "$syncusername" ]; then
		syncusername="$def_syncusername"
		lecho "Using the default '$syncusername"
	fi
	lecho "Using '$syncusername' as the report sync user account name"

	if ! getent passwd "$syncusername"; then
		lecho "Creating the StorPool report sync user account '$syncusername'"
		useradd -m -p '*'  "$syncusername"
	fi
	ssh_id="/home/$syncusername/.ssh/id_rsa"
	if [ ! -f "$ssh_id" ]; then
		lecho "Generating passwordless public/private key-pair for '$syncusername'"
		su -c "ssh-keygen -q -t rsa -b 4096 -f '$ssh_id' -N ''" - "$syncusername"
	fi

	if [ -n "$qflag" ]; then
		exec 1>&9 9>&-
	fi

	mkdir -p /etc/storpool.conf.d
	lecho "Setting SP_CRASH_USER in $repuserconf"
	cat > "$repuserconf" <<EOCONFIG
#
# AUTOGENERATED FILE -- DO NOT EDIT -- CHANGES WILL BE LOST!
#
# This file is autogenerated by the StorPool installation procedure
# Do not edit it directly; if needed, override the setting in another config file
# or, preferably, rerun the StorPool installation scripts!
#

SP_CRASH_USER=$syncusername
EOCONFIG
fi

unset installed_kmod

apiip_etc='/etc/storpool/api-ip'
apiip_lib='/usr/lib/storpool/api-ip'

splibconfget='/usr/lib/storpool/confget'
if echo "$modules" | fgrep -qwe config; then
	if [ -e "$splibconfget" ] && [ ! -f "$splibconfget" ] && [ ! -L "$splibconfget" ]; then
		lerror "Neither a file nor a symlink: $splibconfget"
		exit 1
	fi
fi

systemdlib='/lib/systemd/system'
unset installed_systemd
for mod in $modules; do
	if [ -d "$mod/usr" ]; then
		copydir "$mod/usr/" /usr/

		progs='mgmt server block beacon bridge controller iscsi nvmed stat'
		for prog in $progs; do
			if [ -f "$mod/usr/sbin/storpool_$prog.bin" ]; then
				$noop ln -sf /usr/sbin/storpool_daemon /usr/sbin/storpool_"$prog"
			fi
		done

		if [ -d "$mod/usr$systemdlib" ]; then
			installed_systemd=1
		fi

		if [ -f "$mod/$apiip_lib" ]; then
			$noop mkdir -p -- "$(dirname -- "$apiip_etc")"
			if [ -L "$apiip_etc" ] && [ ! -e "$apiip_etc" ]; then
				$noop rm -- "$apiip_etc"
			fi
			if [ ! -e "$apiip_etc" ]; then
				$noop ln -s "$apiip_lib" "$apiip_etc"
			fi
		fi

		if [ -f "$mod/usr/lib/storpool/bridge-ip" ]; then
			$noop mkdir -p -- "/etc/storpool"
			if [ ! -f /etc/storpool/bridge-ip ]; then
				$noop ln -s "/usr/lib/storpool/bridge-ip" "/etc/storpool/"
			fi
		fi

		if [ -f "$mod/usr/lib/storpool/irqbalance_banscript" ]; then
			$noop ln -sf irqbalance_banscript /usr/lib/storpool/irqbalance_policyscript
		fi
	fi

	if [ -d "$mod/etc" ]; then
		copydir -I -x init.d "$mod/etc/" /etc/
	fi

	if [ -d "$mod/etc/init.d" ]; then
		copydir -I "$mod/etc/init.d/" /etc/init.d/
	fi

	if [ -d "$mod/lib" ]; then
		if [ -d "$mod/lib/modules" ]; then
			installed_kmod=1

			for kver in $kernel_versions; do
				extradir="/lib/modules/$kver/extra"
				[ -d "$extradir" ] || $noop install -d -o root -g root -m 755 "$extradir"
				copydir "$mod$extradir/" "$extradir/"
			done
		fi

		for sub in $(cd -- "$mod" && find lib/ -mindepth 1 -maxdepth 1 -type d \! -name 'modules'); do
			copydir "$mod/$sub/" "/$sub/"
		done
	fi

	if [ -d "$mod$systemdlib" ] && [ -d "$systemdlib" ]; then
		copydir "$mod$systemdlib/" "$systemdlib/"
		installed_systemd=1
	fi
	
	if [ "$mod" = 'common' ]; then
		unset sysrot
		for f in syslog rsyslog; do
			n="/etc/logrotate.d/$f"
			if [ -f "$n" ]; then
				sysrot="$n"
				break
			fi
		done
		if [ -z "$sysrot" ]; then
			lerror 'Could not locate a syslog-like logrotate.d template!'
			exit 1
		fi
		storrot='/etc/logrotate.d/storpool'
		lecho "Creating $storrot"
		$noop /usr/lib/storpool/adapt-config -m logrotate -f "$sysrot" -t /usr/lib/storpool/adapt/logrotate.d/storpool -o "$storrot"
	fi

	if [ "$mod" = 'repsync' ]; then
		if [ -z "$qflag" ]; then
			rsverbose='-v'
		else
			rsverbose=''
		fi
		$noop /usr/sbin/storpool_repsync_crontab $rsverbose -u "$syncusername"
	fi

	if [ "$mod" = 'config' ]; then
		if [ ! -L "$splibconfget" ]; then
			if [ -e "$splibconfget" ]; then
				$noop rm -- "$splibconfget"
			fi
			$noop ln -s -- /usr/bin/confget "$splibconfget"
		fi
	fi
done

if echo "$modules" | fgrep -qwe 'bridge'; then
	brdir='/usr/lib/storpool/bridge'
	if [ ! -d "$brdir" ]; then
		$noop install -d -o root -g root -m 0755 "$brdir"
	fi
fi

workdir="`get_workdir`"
[ -n "$workdir" ] || exit 1
$noop mkdir -p -- "$workdir/logs"

reportdir="`get_reportdir`"
[ -n "$reportdir" ] || exit 1
confsyncuser="`get_conf_syncusername src`"
: "${confsyncuser:=root}"

$noop mkdir -p -- "$reportdir"
$noop chown -- "$confsyncuser" "$reportdir"
$noop chmod 0700 -- "$reportdir"
if [ -d "$reportdir" ]; then
	find -- "$reportdir" -mindepth 1 -maxdepth 1 -type f -name 'report*' -print0 | \
		xargs -0r -- $noop chmod 0600 --
	find -- "$reportdir" -mindepth 1 -maxdepth 1 -type f -name 'report*' -print0 | \
		xargs -0r -- $noop chown -- "$confsyncuser"
fi

DEVLISTENERPATH='/var/run/storpool'
if [ "$workdir" != "$DEVLISTENERPATH" ] && [ ! -d "$DEVLISTENERPATH" ]; then
	$noop mkdir -- "$DEVLISTENERPATH"
	$noop chown root:root -- "$DEVLISTENERPATH"
	$noop chmod 755 -- "$DEVLISTENERPATH"
fi
vlibdir='/var/lib/storpool'
[ -d "$vlibdir" ] || $noop install -d -o root -g root -m 755 "$vlibdir"

logdir='/var/log/storpool'
[ -d "$logdir" ] || $noop install -d -o root -g root -m 755 "$logdir"

if [ -n "$installed_kmod" ]; then
	lecho 'Cleaning out any stale modules in weak-updates/ directories'
	for kver in $kernel_versions; do
		weakdir="/lib/modules/$kdir/weak-updates"
		[ ! -d "$weakdir" ] || find "$weakdir/" -type l -name 'storpool_*.ko' $finddelete -print || true
		if [ -f "/boot/vmlinuz-$kver" ]; then
			$noop depmod -a -- "$kver"
		fi
	done
fi

add_grub_parameters

sphugepages='/usr/sbin/storpool_hugepages'
if [ -f "$sphugepages" ] && [ -x "$sphugepages" ]; then
	lecho 'Running storpool_hugepages'
	if ! $noop "$sphugepages" >> "$install_log" 2>&1; then
		lerror "Ignoring the storpool_hugepages failure; please see the $install_log file for more information"
	fi
fi

if [ -n "$installed_systemd" ] && [ -d '/run/systemd/system' ]; then
	lecho 'Reloading the systemd service database'
	$noop systemctl daemon-reload
fi

lecho 'Removing files from old versions of StorPool'
ldebug "Modules: $modules"
rexp='^('
for m in $modules; do
	m_esc="$(printf -- '%s' "$m" | sed -e 's/[^a-zA-Z-]/\\&/g')"
	rexp="$rexp$m_esc|"
done
rexp="${rexp%|})\$"
awk -v rexp="$rexp" '$1 ~ rexp { print $2 }' remove-files.txt | while read fname; do
	if [ -e "$fname" ]; then
		$noop rm -fv -- "$fname"
	fi
done

run_helper postinst
rm -f -- /var/run/install-storpool.json

if [ -z "$nosync" ]; then
	sync
fi

unset qflag
lecho "Successfully installed $modules"
