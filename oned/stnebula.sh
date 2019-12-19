#!/bin/bash
#if you need sshd to be started uncomment these two beneath
#/usr/bin/ssh-keygen -A
#/usr/sbin/sshd -p 22 -E /var/log/ssh.log
#echo "Sonic2005" | /bin/passwd --stdin root
/usr/bin/oned -f
#ping localhost -c 3 -i 5 2>&1 >/dev/null
#tail -f /var/log/one/one*
