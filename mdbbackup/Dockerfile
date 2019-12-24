FROM alpine:latest
COPY backupmdb.sh /etc/periodic/daily
COPY check.sh /check.sh
ARG dbpass

RUN apk update && \
    apk add --no-cache mariadb-client && \
    chmod a+x /etc/periodic/daily/* && \
    chmod a+x /check.sh && \
    echo -e "[mysqldump] \nuser=oneadmin \npassword=$dbpass \n[client] \nuser=oneadmin \npassword=Sonic2005" > /etc/my.cnf.d/mysqldump.cnf



ENTRYPOINT ["/check.sh"]
