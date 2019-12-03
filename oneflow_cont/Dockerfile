FROM localhost/sharx/base 
MAINTAINER SharxDC

#COPY stnebula.sh /entrypoint.sh
#RUN /bin/chmod +x /entrypoint.sh

RUN  yum -y install --setopt=tsflags=nodocs opennebula-flow && \
     yum -y update && yum clean all 

EXPOSE 2474

USER 9869
#ENTRYPOINT ["/entrypoint.sh"]
ENTRYPOINT ["/usr/bin/ruby", "/usr/lib/one/oneflow/oneflow-server.rb"]
