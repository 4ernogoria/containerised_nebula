FROM alpine:latest
COPY backupmdb.sh /etc/periodic/daily
COPY check.sh /check.sh
ARG dbpass 
ENV userpass $dbpass
RUN apk update && \
    apk add --no-cache mariadb-client && \
    adduser -u 9869 -D  oneadmin && \
    mkdir -p /var/log/mariadb/ && \
    chmod 777 /var/log/mariadb && \
    chmod a+x /etc/periodic/daily/* && \
    chmod a+x /check.sh && \
    echo -e "[mysqldump] \nhost=127.0.0.1 \nuser=oneadmin \npassword=$userpass \n[client] \nhost=127.0.0.1 \nuser=oneadmin \npassword=$userpass" > /etc/my.cnf.d/mysqldump.cnf

USER 9869

ENTRYPOINT ["/check.sh"]
