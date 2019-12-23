#!/bin/bash
read -p 'oneadmin default password? (default=Sonic2005): ' onedpass
if [ -z $onedpass ]
then onedpass=Sonic2005
fi
read -p 'pods volume data folder? (default=/opt): ' deffold
if [ -z $deffold ]
then deffold=/opt
fi
read -p 'mariadb backup folder? (default=mback): ' mbackvol
if [ -z $mbackvol ]
then mbackvol=mback
fi
read -p 'mariadb img name? (default=mdb): ' mdbnm
if [ -z $mdbnm ]
then mdbnm=mdb
fi
read -p 'mariadb root passwd? (default=Sonic2005): ' mdbroot
if [ -z $mdbroot ]
then mdbroot=Sonic2005
fi
read -p 'mariadb oneadmin passwd? (default=Sonic2005): ' mdbusr
if [ -z $mdbusr ]
then mdbusr=Sonic2005
fi
read -p 'mariadb db volume? (default=mysql): ' mdbvol
if [ -z $mdbvol ]
then mdbvol=mysql
fi
read -p 'log volume? (default=log): ' logvol
if [ -z $logvol ]
then logvol=log
fi
read -p 'base img name? (default=baseimg): ' basenm
if [ -z $basenm ]
then basenm=baseimg
fi
read -p 'oned img name? (default=oned): ' onednm
if [ -z $onednm ]
then onednm=oned
fi
read -p 'scheduler img name? (default=sched): ' schednm
if [ -z $schednm ]
then schednm=sched
fi
read -p 'nginx img name? (default=nginx): ' nginxnm
if [ -z $nginxnm ]
then nginxnm=nginx
fi
read -p 'flow img name? (default=flow): ' flownm
if [ -z $flownm ]
then flownm=flow
fi
read -p 'gate img name? (default=gate): ' gatenm
if [ -z $gatenm ]
then gatenm=gate
fi
read -p 'volume for etc/one files (default=etc)' etcfiles
if [ -z $etcfiles ]
then etcfiles="etc"
fi
read -p 'volume for var/lib/one files (default=var)' varfiles
if [ -z $varfiles ]
then varfiles="var"
fi
read -p "pod's name (default=onepod)" podsnm
if [ -z $podsnm ]
then podsnm="onepod"
fi
read -p "pod's publised to the host web port (default=8080)" podwport
if [ -z $podwport ]
then podwport="8080"
fi
read -p "pod's publushed to the host noVNC port (default=29876)" podvncport
if [ -z $podvncport ]
then podvncport="29876"
fi

fullbasenm=localhost/"$basenm"
currpath=$(/bin/pwd)
setenforce 0
sed 's/SELINUX=disabled/SELINUX=disabled/' /etc/selinux/config
cd mariadb
podman build -t "$mdbnm" .
cd ../baseimg
podman build -t "$basenm" .
cd ../oned
podman build --build-arg image="$fullbasenm" -t "$onednm" .
cd ../sched
podman build --build-arg image="$fullbasenm" -t "$schednm" .
cd ../nginx 
podman build --build-arg image="$fullbasenm" -t "$nginxnm" .
cd ../flow
podman build --build-arg image="$fullbasenm" -t "$flownm" .
cd ../gate
podman build --build-arg image="$fullbasenm" -t "$gatenm" .
cd ../mdbbackup
podman build --build-arg dbpass="$mdbusr" -t "mdback" .
cd ../

if [ -d "$deffold" ]
then
        echo "main folder exists"
else
        mkdir -p -m 777 "$deffold"
fi
mkdir "$deffold"/"$logvol" "$deffold"/"$varfiles" "$deffold"/"$etcfiles" "$deffold"/"$mdbvol" "$deffold"/"$varfiles"/.one "$deffold"/"$mbackvol"
echo "oneadmin:$onedpass" > "$deffold"/"$varfiles"/.one/one_auth
if [ "$(ls $deffold"/"$varfiles/.one | grep -v one_auth | wc -l)" -gt 0 ]
then
        echo "something has found in var/.one, probably you've gotten a previous config"
else
        cd "$deffold"/"$etcfiles" && tar -xvf $currpath/etcdraft.tar && \
        cd "$deffold"/"$varfiles" && tar -xvf $currpath/vardraft.tar && \
        chown -R 9869:9869 "$deffold"/"$etcfiles" "$deffold"/"$varfiles" && \
        chown -R 27:27 "$deffold"/"$mdbvol" "$deffold"/"$mbackvol" && \
        chmod -R 777 "$deffold"/"$logvol"
fi

podman pod create --name $podsnm --publish "$podwport":80 --publish "$podvncport":29876
podman run -dt --pod $podsnm --name=mdb -e MYSQL_ROOT_PASSWORD="$mdbroot" -e MYSQL_USER=oneadmin -e MYSQL_PASSWORD="$mdbusr" -e MYSQL_DATABASE=opennebula  -v "$deffold"/"$mdbvol":/var/lib/mysql -v "$deffold"/"$logvol":/var/log/mariadb "$mdbnm"
sleep 10
podman run -dt --pod $podsnm --name=onedpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$onednm"
sleep 5
podman run -dt --pod $podsnm --name=schedpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$schednm"
podman run -dt --pod $podsnm --name=nginxpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$nginxnm"
podman run -dt --pod $podsnm --name=gatepod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$gatenm"
podman run -dt --pod $podsnm --name=flowpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$flownm"
podman run -dt --pod $podsnm --name=mback -v "$deffold"/"$logfiles":/var/log/ -v "$deffold"/"$mbackvol":/opt/mysql/backup "$mdback"

