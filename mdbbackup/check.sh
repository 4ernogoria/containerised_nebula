#!/bin/sh
rm -rf /opt/log/check.file
filecheck=$(ls /opt/log/.one | grep -v one_auth | wc -l)
mysqlcheck=$(mysql -sNe "select count(table_name) from INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA='opennebula';")
if [ "$filecheck" -gt 0 -a $mysqlcheck -gt 0 ]
then
	echo "$(date) the data already has taken its place" >> /var/log/checker.log
else
	echo "$(date) data wasn't found, need to be created" >> /var/log/checker.log
	touch /opt/log/check.file
fi
tail -f /var/log/*.log
