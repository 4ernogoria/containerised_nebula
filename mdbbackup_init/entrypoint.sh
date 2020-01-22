#!/bin/sh
/usr/bin/crontab -u oneadmin /home/oneadmin/crontab
/usr/sbin/crond -L /var/log/mariadb/db_backup_cron.log -l 8 -f
