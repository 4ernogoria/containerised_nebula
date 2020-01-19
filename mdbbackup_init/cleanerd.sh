#!/bin/bash
folder_d=/opt/mysql/backup
filename=$(find $folder_d -type f | sort -n | head -n 1)
echo $filename
mv "$filename" $folder_d/daily/
rm -f $folder_d/* 2&>/dev/null

