# containerised_nebula

!!! Since eventually the containers IP will lose the sense inside a pod, they are defined temporarily.

Basically, currently it works like:
add the execution bit to start.sh; start it from the cloned directory. It's gonna ask you a number of questions, and if the podman's IPnetwork space of yours was (10.88.0.0/24), it will build a set of images and start up containers based on them respectively, with given parameters.

--- old version ---
The Mariadb container stays aside, it is built from centos7 and contains no database by default, just needs to be set during installation a number of parameters like:

podman run -dt --ip=IPADDR --name=CONTNAME -e MYSQL_ROOT_PASSWORD=ROOTPASS -e MYSQL_USER=oneadmin -e MYSQL_PASSWORD=ONEADMINPASS -e MYSQL_DATABASE=opennebula  -v MARIADBVOLUME:/var/lib/images -p MARIADBPORT:3306 IMAGENAMEYOU'veBUILT

The Base container contains most of apps needed, except those NGINX-PASSENGER requires. And in the nutshell other containers just start a tiny layer above, starting a defined funtion. Which are:
  - oned (by oned as the entrypoint);
  - mm-sched (the state of it controlled by a scrypt, since its naturally daemonised nature);
  - Nginx-passenger-sunstone (works not exactly containerly, starts a bunch of services, but the nginx's crash causes a container's death);
  - oneflow and onegate (started as entrypoints, which means the crash is causing the containers death).

Naturally a command running all up is:
podman run -dt --ip=IPADDR --name=CONTAINERNAME -v VARVOLUME:/var/lib/one -v ETCVOLUME:/etc/one -p HOSTPORT:CONTAINERPORT  IMAGE_TO_USE 

NEEDS to be added:
1) SSH no fingerprint check; Probably have to add an ssh daemon
