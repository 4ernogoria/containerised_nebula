FROM centos:7
MAINTAINER SharxDC

COPY nebula.repo /etc/yum.repos.d/

RUN yum -y install --setopt=tsflags=nodocs epel-release && \
    yum -y install --setopt=tsflags=nodocs opennebula-server \
                                           redhat-lsb-core \
                                           opennebula-ruby \
                                           opennebula-node-kvm \
                                           opennebula-common  \
                                           opennebula-sunstone && \
    yum -y update && yum clean all && \
    mkdir -p /temp/etc && \
    mkdir -p /temp/var && \
    chown -R 9869:9869 /etc/one /temp && \
    mv /etc/one/* /temp/etc && \
    mv /var/lib/one/* /temp/var && \  
    gem install bundler --version '<2.0' && \
    echo '1\n' | /usr/share/one/install_gems --yes


#USER 9869
#ENTRYPOINT /usr/local/bin/stnebula.sh
