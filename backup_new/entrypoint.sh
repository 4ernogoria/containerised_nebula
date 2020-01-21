#!/bin/bash
touch /etc/crontab /etc/cron.*/*
rsyslogd
/usr/sbin/crond -n -s

