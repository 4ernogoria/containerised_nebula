FROM centos:7

MAINTAINER SharxDC
COPY mariadb.repo /etc/yum.repos.d/mariadb.repo
RUN yum -y install --setopt=tsflags=nodocs epel-release && \ 
    useradd -u 9869 mysql && \
    yum -y install --setopt=tsflags=nodocs MariaDB-server pwgen psmisc hostname && \ 
    yum -y erase vim-minimal && \
    yum -y update && yum clean all

# Fix permissions to allow for running on openshift
COPY *.sh /
RUN /bin/chmod +x /fix-permissions.sh /entrypoint.sh && \
    mkdir -p /var/log/mariadb && \
    /fix-permissions.sh /var/lib/mysql/   && \
    /fix-permissions.sh /var/log/mariadb/ && \
    /fix-permissions.sh /var/run/

#COPY entrypoint.sh /entrypoint.sh
#RUN /bin/chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

USER 9869 

EXPOSE 3306
CMD ["mysqld_safe"]
