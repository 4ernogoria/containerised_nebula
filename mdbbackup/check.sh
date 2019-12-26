#!/bin/sh
rm /var/log/mariadb/check.file  2&>/dev/null # path might be replaced with a variable
if [ $? ]
then
echo "$(TZ='Europe/Moscow' date '+%H:%M:%S %d:%m:%Y') check.file was removed sucessfully during the container's start"  >> /var/log/mariadb/checker.log
else
echo "$(TZ='Europe/Moscow' date '+%H:%M:%S %d:%m:%Y') check.file wasn't removed during the container's start" >> /var/log/mariadb/checker.log
fi
filecheck=$(ls /opt/var/.one | grep -v one_auth | wc -l) #it needs to be replaced with a variable from the main start.sh script
mysqlcheck=$(mysql -sNe "select count(table_name) from INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA='opennebula';")
if [ "$filecheck" -gt 1 -a $mysqlcheck -gt 0 ] #checks contnets of /var/lib/one/.one if it has more than 2 files and the querry to the database returns more than 0 tables in opennebula DB, nebula's considered already instantiated
then
	echo "$(TZ='Europe/Moscow' date '+%H:%M:%S %d:%m:%Y') the data already has taken its place" >> /var/log/mariadb/checker.log # path might be replaced with a variable
else
	echo "$(TZ='Europe/Moscow' date '+%H:%M:%S %d:%m:%Y') previous nebula data wasn't found, createing check.file (which trigers /etc/one/* /var/lib/one/* overwritting ) " >> /var/log/mariadb/checker.log # path might be replaced with a variable
	touch /var/log/mariadb/check.file
fi
sudo crond -f -l 8 -L /var/log/mariadb/checker.log # path might be replaced with a variable
