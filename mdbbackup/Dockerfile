FROM alpine:latest
COPY backupmdb.sh /etc/periodic/daily
ARG dbpass

RUN apk update && \
    apk add --no-cache mariadb-client && \
    chmod a+x /etc/periodic/daily/* && \
    echo -e "[mysqldump] \nuser=oneadmin \npassword=$dbpass" > /etc/my.cnf.d/mysqldump.cnf
