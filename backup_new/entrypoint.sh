#!/bin/bash
touch /etc/crontab /etc/cron.*/*
crontab -u oneadmin /etc/crontab
rsyslogd
/usr/sbin/crond -n -s
