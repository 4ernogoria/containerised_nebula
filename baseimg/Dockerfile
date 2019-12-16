FROM centos:7
MAINTAINER SharxDC

COPY *.repo /etc/yum.repos.d/

RUN yum -y update && yum clean all && \
    yum -y install --setopt=tsflags=nodocs epel-release && \
    yum -y install --setopt=tsflags=nodocs opennebula-server \
                                           redhat-lsb-core \
                                           opennebula-gate \
                                           opennebula-flow \
                                           opennebula-ruby \
                                           opennebula-node-kvm \
                                           opennebula-common  \
                                           opennebula-sunstone && \
                                           yum clean all && \
                                           #mkdir -p /temp/etc && \
                                           #mkdir -p /temp/var && \
                                           chown -R 9869:9869 /etc/one
                                           #chown -R 9869:9869 /temp
                                           #mv /etc/one/* /temp/etc && \
                                           #mv /var/lib/one/* /temp/var

