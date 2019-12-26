#!/bin/sh

BACKUP_FOLDER=/opt/mysql/backup
BACKUP_FOLDER_D=/opt/mysql/backup/daily
BACKUP_FOLDER_W=/opt/mysql/backup/weekly
NOW=$(date '+%d%m%Y')

GZIP=$(which gzip)
MYSQLDUMP=$(which mysqldump)

### MySQL Server Login info ###
MHOST=127.0.0.1
MPASS=$mdbusr
MUSER=oneadmin

[ ! -d $BACKUP_FOLDER ] && mkdir -p $BACKUP_FOLDER
[ ! -d $BACKUP_FOLDER_D ] && mkdir -p $BACKUP_FOLDER_D
[ ! -d $BACKUP_FOLDER_W ] && mkdir -p $BACKUP_FOLDER_W

FILE=$BACKUP_FOLDER/backup-$NOW.sql.gz
$MYSQLDUMP -h $MHOST -u $MUSER --log-error=/var/log/mariadb --databases opennebula | $GZIP -9 > $FILE
