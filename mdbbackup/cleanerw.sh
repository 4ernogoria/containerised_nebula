#!/bin/bash
folder_w=/opt/mysql/backup
filename=$(find "$folder_w"/daily -type f | sort -n | head -n 1)
echo $filename
mv "$filename" $folder_d/weekly/
rm -f $folder_w/daily/* 2&>/dev/null
