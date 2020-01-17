FROM centos:7
MAINTAINER SharxDC

COPY *.repo /etc/yum.repos.d/
COPY storpool /root/storpool

RUN yum -y update && yum clean all && \
    yum -y install --setopt=tsflags=nodocs epel-release && \
    yum -y install --setopt=tsflags=nodocs opennebula-server \
                                           MariaDB-shared \
                                           redhat-lsb-core \
                                           opennebula-gate \
                                           opennebula-flow \
                                           opennebula-ruby \
                                           opennebula-node-kvm \
                                           opennebula-common  \
                                           opennebula-sunstone && \
                                           yum clean all && \
                                           mkdir -p /temp/etc && \
                                           mkdir -p /temp/var && \
                                           chown -R 9869:9869 /etc/one && \
                                           echo -e "StrictHostKeyChecking no \nUserKnownHostsFile=/dev/null" >> /etc/ssh/ssh_config && \
                                           chown -R 9869:9869 /temp && \
                                           bash /root/storpool/addon-storpool/install.sh && \
                                           cp /root/storpool/addon-storpoolrc /var/lib/one/remotes/ && \
                                           bash /root/storpool/storpool-18.02.752.1736934/install.sh cli config common && \
                                           cp /root/storpool/storpool.conf /etc/ && \
                                           mv /etc/one/* /temp/etc/ && \
                                           mv /var/lib/one/{.[!.],}* /temp/var/ && \
                                           rm -rf /root/storpool

