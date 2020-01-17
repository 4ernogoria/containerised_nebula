#!/bin/bash

if [ -t 1 ]; then
	bold=$(tput bold)
	norm=$(tput sgr0)
fi

chkloaded(){
	local module="$1"
	if lsmod | grep -Fqe "$module"; then
		return 0
	else
		return 1
	fi
}

_in(){
	local sought="$1"
	local arr=($2)
	local el=''
	for el in "${arr[@]}"; do
		if [[ $sought == "$el" ]]; then
			return 0
		fi
	done
	return 1
}

chkifaces(){
	local ifaces=( $(storpool_showconf -ne SP_IFACE | sed -e "s/,/ /g") )
	local forceflag="$1"
	local net='' ind='' ifcfg=''
	for net in 0 1; do
		ifcfg="$(storpool_showconf -ne "SP_IFACE$((net+1))_CFG")"
		if [[ -z $ifcfg ]]; then
			continue
		fi
		# check newproto config interfaces as well
		# ex. 1:bond0.900:eth2:900:10.3.9.11:b:s:P
		local ifcfgarr=( ${ifcfg//:/ } )
		for ind in 1 2; do
			# ex. bond0.900/eth2
			local iface="${ifcfgarr[$ind]}"
			if [[ -n $iface ]]; then
				if ! _in "$iface" "${ifaces[@]}"; then
					ifaces+=($iface)
				fi
			fi
		done
	done
	# check whether the interfaces exist
	local fail='' carrier='' operstate=''
	for ind in "${!ifaces[@]}"; do
		carrier="$(cat "/sys/class/net/${ifaces[$ind]}/carrier" 2>/dev/null)"
		operstate="$(cat "/sys/class/net/${ifaces[$ind]}/operstate" 2>/dev/null)"
		if [[ -z $carrier ]]; then
			fail=1
			echo "Interface ${ifaces[$ind]} has no carrier" 1>&2
		elif [[ $operstate != up ]]; then
			fail=1
			echo "Interface ${ifaces[$ind]} is not up" 1>&2
		fi
	done
	if [[ -n $fail && -z $forceflag ]]; then
		echo "Bailing out, use --force if you would like to proceed anyway" 1>&2
		exit 1
	fi
}

printmodversion(){
	local mod="$1"
	local srcver='' mpath=''
	mpath="/sys/module/$mod/srcversion"
	if [[ -e $mpath ]]; then
		srcver="$(<"$mpath")"
	else
		srcver="not_loaded"
	fi
	echo -e "$mod\tsrcversion:\t${bold}$srcver${norm}"
}

getservices(){
	local mode="$1"
	case "$mode" in
		'all')
			echo storpool_{beacon,block,server{,_1,_2,_3,_4,_5,_6,_7,_8,_9,_10,_11},mgmt,bridge,iscsi,nvmed,controller}
			;;
		'disk')
			echo storpool_{server{,_1,_2,_3,_4,_5,_6,_7,_8,_9,_10,_11},controller}
			;;
		*)
			echo "No such mode $mode, bailing out" 1>&2
			exit 1
			;;
	esac
}

chkprelinked(){
	local services=($1)
	local errs=''
	if [[ -z ${services[*]} ]]; then
		errs=1
	fi
	for service in "${services[@]}"; do
		if ! /usr/lib/storpool/check_prelinked "$service" "/var/run/$service.pid"; then
			errs=1
		fi
	done
	[ -z "$errs" ] || exit 1
}

getrunning(){
	local services=($1)
	local service=''
	for service in "${services[@]}"; do
		if [[ -x /usr/sbin/$service ]]; then
			if service "$service" status &>/dev/null; then
				echo "$service"
			fi
		fi
	done
}

unloadmodules(){
	local modules=($@)
	local mod=''
	for mod in "${modules[@]}"; do
		printmodversion "$mod"
		rmmod "$mod"
		if chkloaded "$mod" ; then
			echo -e " ${bold}${mod} failed to unload${norm}\n"
		fi
	done
}

loadmodules(){
	local modules=($@)
	local mod=''
	for mod in "${modules[@]}"; do
		modprobe "$mod"
		if ! chkloaded "$mod"; then
			echo "Failed to load $mod" 1>&2
		fi
		printmodversion "$mod"
	done
}

stopservices(){
	local services=($@)
	local count="${#services[*]}"
	local stopservice=''
	while ((--count >= 0)); do
		stopservice="${services[count]}"
		service "$stopservice" stop
	done
}

startservices(){
	local services=($@)
	local count=-1
	local scount="${#services[*]}"
	local startservice=''
	while ((count++ < $((scount-1)))); do
		startservice="${services[count]}"
		service "$startservice" start
	done
}

chkhugepages(){
	# now just attempts to reserve and fails if hugepages exits
	# with non-zero exit status
	if ! command -v storpool_hugepages >/dev/null; then
		echo "Could not find storpool_hugepages, please check" 1>&2
		exit 1
	fi
	cmd=(storpool_hugepages -sv)
	if ! out="$("${cmd[@]}")" ; then
		echo "An atetmpt to execute '${cmd[*]}' failed, output:"
		echo "$out"
		exit 1
	fi
}

chkcgroups(){
	local services=($@)
	local service=''
	# shellcheck disable=SC2154
	if [[ -n $nocgroups ]]; then
		echo "Skipping cgroups check as requested" 1>&2
		return
	fi
	for service in "${services[@]}"; do
		local sstring="$service"
		if [[ $sstring =~ "server" ]]; then
			sstring="${sstring/server_/server}"
		fi
		cgstring="${sstring/storpool_/sp_}_cgroups"
		cgstring="${cgstring^^}"
		cgexecargs="$(storpool_showconf -ne "${cgstring}")"
		if [[ -z $cgexecargs ]]; then
			echo "Could not determine the cgexecargs for $service, bailing out" 1>&2
			exit 1
		fi
		# shellcheck disable=SC2086
		if ! cgexec $cgexecargs echo 'boo' &>/dev/null ; then
			echo "The $service could not be executed in the configured $cgstring, bailing out" 1>&2
			exit 1
		fi
	done
}

chkmodulesupdate(){
	local modules=($(lsmod | grep -Ewo "^storpool_[a-z]+"))
	local mod='' srcversion='' loadedversionf='' loadedversion=''
	# shellcheck disable=SC2154
	if [[ -n $nomodulechecks ]]; then
		echo "Skipping checks for module changes as requested" 1>&2
		return
	fi
	for mod in "${modules[@]}" ; do
		srcversion="$(modinfo "$mod" | grep -Fe srcversion)"
		srcversion="${srcversion##*:}"
		srcversion="${srcversion// }"
		loadedversionf="/sys/module/$mod/srcversion"
		if [[ -e $loadedversionf ]]; then
		  # check if the loaded version is not different
		  loadedversion="$(<"$loadedversionf")"
		  if [[ $srcversion != "$loadedversion" ]]; then
			echo "$mod module installed version $srcversion different from the loaded $loadedversion, bailing out" 1>&2
			exit 1
		  fi
		fi
	done
}
