FROM alpine:latest
COPY backupmdb /etc/periodic/hourly/
COPY check.sh /check.sh
ARG dbpass 
ENV userpass $dbpass
RUN apk update && \
    apk add --no-cache mariadb-client \
                       tzdata \
                       sudo \
                       mariadb-backup && \
    adduser -u 9869 -D  oneadmin && \
    echo -e "oneadmin ALL=(ALL) NOPASSWD: /usr/sbin/crond" > /etc/sudoers.d/onedamin && \
    mkdir -p /var/log/mariadb/ /xtrabackup_backupfiles && \
    chown -R oneadmin /xtrabackup_backupfiles && \
    chmod 777 /var/log/mariadb && \
    chmod a+x /etc/periodic/hourly/* && \
    chmod a+x /check.sh && \
    echo -e "[mysqldump] \nhost=127.0.0.1 \nuser=oneadmin \npassword=$userpass \n[client] \nhost=127.0.0.1 \nuser=oneadmin \npassword=$userpass" > /etc/my.cnf.d/mysqldump.cnf
COPY crontab /etc/crontabs/root

USER 9869
WORKDIR /opt/mysql/backup # should be set by a variable

ENTRYPOINT ["/check.sh"]
