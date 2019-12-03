FROM localhost/sharx/base 
MAINTAINER SharxDC

#COPY stnebula.sh /entrypoint.sh
#RUN /bin/chmod +x /entrypoint.sh

RUN  yum -y install --setopt=tsflags=nodocs opennebula-gate && \
     yum -y update && yum clean all 

EXPOSE 5030

USER 9869
ENTRYPOINT ["/usr/bin/ruby", "/usr/lib/one/onegate/onegate-server.rb"]
