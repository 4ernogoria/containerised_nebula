#!/bin/bash
#touch /etc/crontab /etc/cron.*/*
crontab -u oneadmin /home/oneadmin/crontab
/usr/sbin/crond -s -p -n
