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
                                           #gem install bundler --version '<2.0' && \ not requred for v10
                                           #/usr/share/one/install_gems --yes && \ not required for v10
                                           yum clean all && \
                                           #mkdir -p /temp/etc && \
                                           #mkdir -p /temp/var && \
                                           chown -R 9869:9869 /etc/one && \
                                           echo -e "StrictHostKeyChecking no \nUserKnownHostsFile=/dev/null" >> /etc/ssh/ssh_config
                                           #chown -R 9869:9869 /temp
                                           #mv /etc/one/* /temp/etc && \
                                           #mv /var/lib/one/* /temp/var

