FROM alpine:latest

COPY crontab /home/oneadmin/crontab
COPY  test /home/oneadmin/periodic/15min/test
COPY  mariabackup /home/oneadmin/periodic/hourly/mariabackup
COPY  mysqldump /home/oneadmin/periodic/daily/mysqldump
COPY  cleaner /home/oneadmin/periodic/weekly/cleaner
COPY entrypoint.sh /entrypoint.sh

RUN /sbin/apk update && \
    /sbin/apk add --no-cache mariadb-client \
                       tzdata \
                       sudo \
                       busybox-suid \
                       mariadb-backup && \
    /usr/sbin/adduser -u 9869 -D oneadmin -s /bin/sh && \
#    /bin/echo -e "oneadmin ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/onedamin && \
    /bin/mkdir -p /var/log/mariadb/ /backup /home/oneadmin/periodic/15min /home/oneadmin/periodic/hourly /home/oneadmin/periodic/daily /home/oneadmin/periodic/weekly && \
    /bin/chown -R oneadmin:oneadmin /backup /home/oneadmin && \
    /bin/chmod 777 /var/log/mariadb && \
    /bin/chmod a+x /entrypoint.sh /home/oneadmin/periodic/hourly/* /home/oneadmin/periodic/daily/* /home/oneadmin/periodic/weekly/* /home/oneadmin/periodic/15min/*  && \
#    /usr/bin/crontab -u oneadmin -l /etc/crontabs/oneadmin | /usr/bin/crontab - && \
    /bin/echo -e "[mysqldump] \nhost=127.0.0.1 \nuser=oneadmin \npassword=Sonic2005 \n[client] \nhost=127.0.0.1 \nuser=oneadmin \npassword=Sonic2005" > /etc/my.cnf.d/mysqldump.cnf

ENTRYPOINT ["/entrypoint.sh"]
