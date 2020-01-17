#!/bin/bash
usage(){
	cat <<EOUSAGE
	Usage: '$(basename -- $0)' -c 0-10 [-m allocationGroups] [-g placementGroup]
	Dumps the current state, then runs balancer, all arguments are passed to balancer binary
	Then loads the new state into the running cluster.

	-c - coefficient - between 0 and 10, controls how much data is being relocated
		start with 0 and if not rebalanced well enough test with 6 and 10
		Beware that 10 might relocate lots of data between the drives in the cluster
	-m - number of allocation groups.
		(used when some of the drives are larger than 4T to limit the amount of data )
	-g - rebalance only this cgroup
		(used usually when re-balancing out/in a single drive)
	
EOUSAGE
	exit
}

if [[ -z $@ ]]; then
	usage
	exit 1
else
	args="$@"
fi

unset http_proxy
unset https_proxy

storpool -B balancer stop

. /usr/lib/storpool/storpool_confget.sh

set -e
set -o pipefail

dumped=`date "+%Y-%m-%d-%H-%M-%S"`
mkdir $dumped
cd $dumped

curl -H "Authorization: Storpool v1:$SP_AUTH_TOKEN" "$SP_API_HTTP_HOST:$SP_API_HTTP_PORT/ctrl/1.0/DisksList" > disks.json
curl -H "Authorization: Storpool v1:$SP_AUTH_TOKEN" "$SP_API_HTTP_HOST:$SP_API_HTTP_PORT/ctrl/1.0/PlacementGroupsList" > placement-groups.json
curl -H "Authorization: Storpool v1:$SP_AUTH_TOKEN" "$SP_API_HTTP_HOST:$SP_API_HTTP_PORT/ctrl/1.0/FaultSetsList" > fault-sets.json
curl -H "Authorization: Storpool v1:$SP_AUTH_TOKEN" "$SP_API_HTTP_HOST:$SP_API_HTTP_PORT/ctrl/1.0/VolumeBalancerGroups" > balancer-allocation-groups.json

/usr/lib/storpool/storpool_balancer.bin $args
curl --data-binary @out.json -H "Authorization: Storpool v1:$SP_AUTH_TOKEN" "$SP_API_HTTP_HOST:$SP_API_HTTP_PORT/ctrl/1.0/__BalancerDiskSetsUpdate"
storpool -B balancer disks | tee -a balancer-disks.txt
storpool -B balancer status

echo "Please check if the above looks legit and then run:

storpool balancer commit"
