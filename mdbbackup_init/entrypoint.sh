#!/bin/sh
/usr/bin/crontab -u oneadmin /home/oneadmin/crontab
/usr/sbin/crond -L /backup/test.log -l 8 -f
