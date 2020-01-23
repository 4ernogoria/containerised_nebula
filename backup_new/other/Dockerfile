FROM centos:7

MAINTAINER SharxDC
COPY mariadb.repo /etc/yum.repos.d/mariadb.repo
COPY temp.sh /home/oneadmin/temp
#COPY entrypoint.sh /entrypoint.sh
RUN (cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == \
systemd-tmpfiles-setup.service ] || rm -f $i; done); \
rm -f /lib/systemd/system/multi-user.target.wants/*;\
rm -f /etc/systemd/system/*.wants/*;\
rm -f /lib/systemd/system/local-fs.target.wants/*; \
rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
rm -f /lib/systemd/system/basic.target.wants/*;\
rm -f /lib/systemd/system/anaconda.target.wants/*;
RUN yum -y install --setopt=tsflags=nodocs rsyslog MariaDB-backup MariaDB-client cronie && yum clean all && chmod +x /home/oneadmin/temp && touch /var/log/cron && echo "1-59 * * * * /bin/bash /home/oneadmin/temp" > /home/oneadmin/crontab && adduser -u 9869 oneadmin && mkdir -p /backup && chmod 777 /backup && chown -R oneadmin:oneadmin /home/oneadmin
#ENTRYPOINT ["/entrypoint.sh"]
#ENTRYPOINT ["/usr/sbin/crond","-n"]
CMD ["/usr/sbin/init"]
