FROM localhost/mdbbaseimg

MAINTAINER SharxDC

# Fix permissions to allow for running on openshift
COPY *.sh /
RUN /bin/chmod +x /fix-permissions.sh /entrypoint.sh && \
    mkdir -p /var/log/mariadb && \
    /fix-permissions.sh /var/lib/mysql/   && \
    /fix-permissions.sh /var/log/mariadb/ && \
    /fix-permissions.sh /var/run/

ENTRYPOINT ["/entrypoint.sh"]

USER 9868 

EXPOSE 3306
CMD ["mysqld_safe"]
