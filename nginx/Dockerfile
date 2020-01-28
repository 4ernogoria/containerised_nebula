FROM 4ernogoria/baseimg
MAINTAINER SharxDC

COPY passenger.repo /etc/yum.repos.d/
COPY stnebula.sh /entrypoint.sh
RUN /bin/chmod +x /entrypoint.sh

RUN yum -y install --setopt=tsflags=nodocs epel-release && \
    yum -y install --setopt=tsflags=nodocs yum-utils \
                                           rubygem-rack \
                                           memcached && \
    yum clean all && \
    yum-config-manager --disable epel && \
    yum -y install --setopt=tsflags=nodocs passenger \
                                           nginx && \
    yum -y update && yum clean all && \
    rm -f /etc/nginx/conf.d/nginx.conf && \
    rm -f /etc/nginx/nginx.conf 
    
COPY passenger.conf /etc/nginx/conf.d/
COPY nginx.conf /etc/nginx/

EXPOSE 80 29876
 
STOPSIGNAL SIGTERM

ENTRYPOINT ["/entrypoint.sh"]
