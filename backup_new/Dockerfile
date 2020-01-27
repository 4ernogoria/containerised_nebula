FROM localhost/mdbbaseimg

MAINTAINER SharxDC

COPY temp.sh /cron/scripts/temp
COPY entrypoint.sh /entrypoint.sh
COPY cronie-1.4.11-23.1.el7.x86_64.rpm  /cronie-1.4.11-23.1.el7.x86_64.rpm
COPY cronie-anacron-1.4.11-23.1.el7.x86_64.rpm /cronie-anacron-1.4.11-23.1.el7.x86_64.rpm

RUN yum -y install --setopt=tsflags=nodocs MariaDB-backup MariaDB-client /cronie-1.4.11-23.1.el7.x86_64.rpm /cronie-anacron-1.4.11-23.1.el7.x86_64.rpm && yum clean all && chmod +x /entrypoint.sh /cron/scripts/* && echo "1-59 * * * * /bin/bash /cron/scripts/temp" > /cron/crontab && mkdir -p /backup && useradd -u 9869 oneadmin && chown -R 9869:9869 /cron /backup && rm -f /cronie-1.4.11-23.1.el7.x86_64.rpm /cronie-anacron-1.4.11-23.1.el7.x86_64.rpm

ENTRYPOINT ["/entrypoint.sh"]
