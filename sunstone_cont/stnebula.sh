#!/bin/bash
/usr/bin/memcached -u memcached -p 11211 -m 64 -c 1024 &
ping localhost -c 2 -i 2 2>&1 >/dev/null
/usr/bin/novnc-server start 
/usr/sbin/nginx
#/bin/bash
