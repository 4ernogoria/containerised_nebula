ARG image
FROM "$image"
MAINTAINER SharxDC

#COPY stnebula.sh /entrypoint.sh
#COPY ssh* /etc/ssh/ 
#RUN /bin/chmod +x /entrypoint.sh
RUN mv /temp/var/.ssh /var/lib/one/
EXPOSE 2633

USER 9869
ENTRYPOINT ["oned", "-f"]
#ENTRYPOINT ["/entrypoint.sh"]
