#!/bin/bash
#MariaDB variables to set
mdbip=10.88.0.200
#Oned vars
onedip=10.88.0.201
onedport=2633
#nginx
nginxip=10.88.0.202
nginxport=80
novncport=29876
#Onegate vars
gateip=10.88.0.203
gateport=5030
#Oneflow vars
flowip=10.88.0.204

read -p 'mariadb img name? (default=mdb)' mdbnm
if [ -z $mdbnm ]
then mdbnm=mdb
fi
read -p 'mariadb root passwd? (default=passwd)' mdbroot
if [ -z $mdbroot ]
then mdbroot=passwd
fi
read -p 'mariadm oneadmin passwd? (default=passwd)' mdbusr
if [ -z $mdbusr ]
then mdbusr=passwd
fi
read -p 'mariadm volume? (default=mdb)' mdbvol
if [ -z $mdbvol ]
then mdbvol=mdb
fi
read -p 'base img name? (default=baseimg)' basenm
if [ -z $basenm ]
then basenm=baseimg
fi
read -p 'oned img name? (default=oned)' onednm
if [ -z $onednm ]
then onednm=oned
fi
read -p 'nginx img name? (default=nginx)' nginxnm
if [ -z $nginxnm ]
then nginxnm=nginx
fi
read -p 'flow img name? (default=flow)' flownm
if [ -z $flownm ]
then flownm=flow
fi
read -p 'gate img name? (default=gate)' gatenm
if [ -z $gatenm ]
then gatenm=gate
fi
read -p 'volume for etc files (default=/etc/one)' etcfiles
if [ -z $etcfiles ]
then etcfiles="/etc/one"
fi
read -p 'volume for var files (default=/var/lib/one)' varfiles
if [ -z $varfiles ]
then varfiles="/var/lib/one"
fi
read -p 'volume for logs (default=/log)' logfiles
if [ -z $logfiles ]
then logfiles="/log"
fi
fullbasenm=localhost/"$basenm"

cd mariadb
podman build -t "$mdbnm" .
cd ../baseimg
podman build -t "$basenm" .
cd ../oned
podman build --build-arg image="$fullbasenm" -t "$onednm" .
cd ../nginx 
podman build --build-arg image="$fullbasenm" -t "$nginxnm" .
cd ../flow
podman build --build-arg image="$fullbasenm" -t "$flownm" .
cd ../gate
podman build --build-arg image="$fullbasenm" -t "$gatenm" .
cd ../
podman run -dt --ip="$mdbip" --name=mariadb -e MYSQL_ROOT_PASSWORD="$mdbroot" -e MYSQL_USER=oneadmin -e MYSQL_PASSWORD="$mdbusr" -e MYSQL_DATABASE=opennebula  -v "$mdbvol":/var/lib/images -p $mdbport:3306 "$mdbnm"
sleep 5
podman run -dt --ip="$onedip" --name=oned -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -p $onedport:2633 "$onednm"
sleep 5
podman run -dt --ip="$nginxip" --name=nginx -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -p "$novncport":29876 -p $nginxport:80 "$nginxnm"
podman run -dt --ip="$flowip" --name=flow -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one  "$flownm"
podman run -dt --ip="$gateip" --name=gate -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -p $gateport:5030 "$gatenm"
