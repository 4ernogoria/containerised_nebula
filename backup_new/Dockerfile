FROM centos:7

MAINTAINER SharxDC
COPY mariadb.repo /etc/yum.repos.d/mariadb.repo
COPY temp.sh /home/oneadmin/temp
COPY entrypoint.sh /entrypoint.sh
RUN yum -y install --setopt=tsflags=nodocs rsyslog MariaDB-backup MariaDB-client cronie && yum clean all && chmod +x /entrypoint.sh /home/oneadmin/temp && touch /var/log/cron && echo "1-59 * * * * /bin/bash /home/oneadmin/temp" > /etc/crontab && adduser -u 9869 oneadmin && mkdir /backup && chmod 777 /backup
ENTRYPOINT ["/entrypoint.sh"]
#ENTRYPOINT ["/usr/sbin/crond","-n"]
