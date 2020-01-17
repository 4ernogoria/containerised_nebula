#!/bin/sh
LD_PRELOAD=/usr/lib/storpool/bpf_preload.so tcpdump "$@"
