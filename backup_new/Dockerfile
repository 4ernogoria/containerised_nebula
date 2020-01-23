FROM centos:7

MAINTAINER SharxDC
COPY mariadb.repo /etc/yum.repos.d/mariadb.repo
COPY temp.sh /home/oneadmin/temp
COPY entrypoint.sh /entrypoint.sh
COPY cronie-1.4.11-23.1.el7.x86_64.rpm  /cronie-1.4.11-23.1.el7.x86_64.rpm
COPY cronie-anacron-1.4.11-23.1.el7.x86_64.rpm /cronie-anacron-1.4.11-23.1.el7.x86_64.rpm
RUN yum -y install --setopt=tsflags=nodocs rsyslog MariaDB-backup MariaDB-client /cronie-1.4.11-23.1.el7.x86_64.rpm /cronie-anacron-1.4.11-23.1.el7.x86_64.rpm && yum clean all && chmod +x /entrypoint.sh /home/oneadmin/temp && touch /var/log/cron && echo "1-59 * * * * /bin/bash /home/oneadmin/temp" > /home/oneadmin/crontab && adduser -u 9869 oneadmin && mkdir -p /backup && chmod 777 /backup && chown -R oneadmin:oneadmin /home/oneadmin
ENTRYPOINT ["/entrypoint.sh"]
#ENTRYPOINT ["/usr/sbin/crond","-n"]
