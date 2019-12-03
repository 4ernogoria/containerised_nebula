#!/bin/bash
/usr/bin/mm_sched
while [ "$(ps aux | grep mm_sched | grep -v grep)" ]
do
sleep 10
done

