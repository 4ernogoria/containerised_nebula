ARG image
FROM "$image"
MAINTAINER SharxDC

COPY stnebula.sh /entrypoint.sh
RUN /bin/chmod +x /entrypoint.sh

USER 9869
ENTRYPOINT ["/entrypoint.sh"]
