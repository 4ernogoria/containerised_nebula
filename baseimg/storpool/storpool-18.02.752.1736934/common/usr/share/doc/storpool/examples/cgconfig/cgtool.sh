#!/bin/bash
#
#-
# Copyright (c) 2015  StorPool.
# All rights reserved.
#

set -e

memtotal_kB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
memtotal=$((memtotal_kB*1024))
align=20
MiB=$((1024*1024))
GiB=$((1024*1024*1024))

memshow()
{
	local var k=1024
	while [ -n "$*" ]; do
		eval var=\$$1
		printf "%${align}s %d %dM %dG\n" $1 $var $(((var+(MiB-1))/MiB)) $(((var+(GiB-1))/GiB))
		shift
	done
}

is_systemd=0
if readlink -f /sbin/init | grep -q systemd 2>&1 >/dev/null; then
	is_systemd=1
fi

declare -A memories cpusets_cpus cpusets_mems cpusets_cpu_exclusive cgid currentLimits

while read cgl; do
	cg=${cgl%%:*}
	slice=${cgl#*:}
	[ "${slice##*/}" = "${slice#*/}" ] || continue
	case "$cg" in
		memory)
			while IFS='\n' read l; do
				l=${l#*:}
				v=${l##*[[:space:]]}
				k=${l%[[:space:]]*}
				eval $k=$v
			done < <(cgget -n -r "memory.stat" "$slice")
			total_cache_rss=$((total_cache + total_rss))
			memories[${cg}${slice}]=$total_cache_rss
			currentLimits[${cg}${slice}]=$hierarchical_memory_limit
			;;
		cpuset)
			cpus=$(cgget -n -r "cpuset.cpus" "$slice" | awk '{print $2}')
			mems=$(cgget -n -r "cpuset.mems" "$slice" | awk '{print $2}')
			excl=$(cgget -n -r "cpuset.cpu_exclusive" "$slice" | awk '{print $2}')
			cpusets_cpus[${cg}${slice}]=$cpus
			cpusets_mems[${cg}${slice}]=$mems
			cpusets_cpu_exclusive[${cg}${slice}]=$excl
			echo "*** ${cg}:$slice exclusive:$excl mems:$mems cpus:$cpus"
			;;
	esac
done < <(lscgroup)

#memshow "memtotal"

leftmem=$memtotal

cglist="memory/storpool.slice memory/user.slice memory/system.slice memory/machine.slice"

for c in $cglist; do
	cg=${c##*/}
	[ $is_systemd -eq 0 ] && [ "$cg" = "user.slice" ] && continue
	rlimit=${memories[$c]}
	case "$cg" in
		storpool.slice)
			rlimit=$(( rlimit + (2*GiB) ))
			leftmem=$(( leftmem - rlimit ))
			;;
		system.slice)
			rlimit=$(( rlimit + (1*GiB) ))
			leftmem=$(( leftmem - rlimit ))
			;;
		user.slice)
			rlimit=$(( rlimit + (1*GiB) ))
			leftmem=$(( leftmem - rlimit ))
			;;
		machine.slice)
			rlimit=$(( leftmem - (1*GiB) ))
			;;
	esac
	limit=$(((rlimit+MiB-1)/MiB))M
	mem=${memories[$c]}
	currentLimit=${currentLimits[$c]:-0}
	echo "*** memory:/$cg Currently in use $((mem/MiB))M, Current limit $((currentLimit/MiB))M, Suggested limit $limit of $((memtotal/MiB))M"
done
