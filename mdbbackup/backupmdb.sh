#!/bin/sh

BACKUP_FOLDER=/opt/mysql/backup
NOW=$(date '+%d%m%Y')

GZIP=$(which gzip)
MYSQLDUMP=$(which mysqldump)

### MySQL Server Login info ###
MHOST=127.0.0.1
MPASS=$mdbusr
MUSER=oneadmin

[ ! -d $BACKUP_FOLDER ] && mkdir -p $BACKUP_FOLDER

FILE=$BACKUP_FOLDER/backup-$NOW.sql.gz
$MYSQLDUMP -h $MHOST -u $MUSER --log-error=/var/log/mysql --databases opennebula | $GZIP -9 > $FILE
