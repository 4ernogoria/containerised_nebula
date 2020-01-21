#!/bin/bash
BACKUP_FOLDER=/opt/mysql/backup/daily
export $BACKUP_FOLDER

filename=$(find $folder_d -type f | sort -n | head -n 1)
echo $filename
cp "$filename" $folder_d/daily/
rm -f $folder_d/* 2&>/dev/null

