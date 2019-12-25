#!/bin/bash
read -p 'backup imgname? (default=backup): ' backnm
if [ -z $backnm ]
then backnm=backup
fi
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
## needed for user root to connect to db
#echo -e "[client] \nuser=root \npassword='mdbroot'" > /root/.my.cnf && chmod 400 /root/.my.cnf

if [ -d "$deffold" ]
then
        echo "main folder exists, proceed"
else
        echo "the folder does not exist, check if the volume mounted correctly" | logger
	exit
fi

if [ -f /opt/log/check.file ] ## the file, if created, by mdbbackup container shows the need to instatiate a prestart configuration  
then
        echo "the /opt/log/check.file has been found, preconfiguration is required" 2>&1 | logger
        mkdir -p "$deffold"/"$logvol" "$deffold"/"$varfiles" "$deffold"/"$etcfiles" "$deffold"/"$mdbvol" "$deffold"/"$varfiles"/.one "$deffold"/"$mbackvol" 2>&1 | logger
        chown -R 9869:9869 "$deffold" "$deffold"/"$logvol" "$deffold"/"$varfiles" "$deffold"/"$etcfiles" "$deffold"/"$mdbvol" "$deffold"/"$varfiles"/.one "$deffold"/"$mbackvol"
        chmod 770 "$deffold" "$deffold"/"$logvol" "$deffold"/"$varfiles" "$deffold"/"$etcfiles" "$deffold"/"$mdbvol" "$deffold"/"$varfiles"/.one "$deffold"/"$mbackvol"
        echo "oneadmin:$onedpass" > "$deffold"/"$varfiles"/.one/one_auth
        useradd -u 9869 -M -s /sbin/nologin oneadmin 2>&1 | logger
        cd "$deffold"/"$etcfiles" && tar -xvf $currpath/etcdraft.tar 2>&1 | logger
        cd "$deffold"/"$varfiles" && tar -xvf $currpath/vardraft.tar 2>&1 | logger
        chown -R 9869:9869 "$deffold"/"$etcfiles" "$deffold"/"$varfiles"
else
	echo "file has not been found, no need to do anything, just start containers" 2>&1 | logger
fi
#dbquerry=$(mysql -sNe "select count(table_name) from INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA='opennebula';")
cd $currpath/mariadb
podman build -t "$mdbnm" .
cd  $currpath/baseimg
podman build -t "$basenm" .
cd  $currpath/oned
podman build --build-arg image="$fullbasenm" -t "$onednm" .
cd  $currpath/sched
podman build --build-arg image="$fullbasenm" -t "$schednm" .
cd  $currpath/nginx 
podman build --build-arg image="$fullbasenm" -t "$nginxnm" .
cd  $currpath/flow
podman build --build-arg image="$fullbasenm" -t "$flownm" .
cd  $currpath/gate
podman build --build-arg image="$fullbasenm" -t "$gatenm" .
cd  $currpath/mdbbackup
podman build --build-arg dbpass="$mdbusr" -t "$backnm" .
cd  $currpath/

podman pod create --name $podsnm --publish "$podwport":80 --publish "$podvncport":29876
podman run -dt --pod $podsnm --name=mdb -e MYSQL_ROOT_PASSWORD="$mdbroot" -e MYSQL_USER=oneadmin -e MYSQL_PASSWORD="$mdbusr" -e MYSQL_DATABASE=opennebula  -v "$deffold"/"$mdbvol":/var/lib/mysql -v "$deffold"/"$logvol":/var/log/mariadb "$mdbnm"
sleep 5
podman run -dt --pod $podsnm --name=mbackup -v "$deffold"/"$logfiles":/var/log/mariadb -v "$deffold"/"$mbackvol":/opt/mysql/backup -v "$deffold"/"$varfiles":/opt/var "$backnm"
sleep 5
podman run -dt --pod $podsnm --name=onedpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$onednm"
sleep 5
podman run -dt --pod $podsnm --name=schedpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$schednm"
podman run -dt --pod $podsnm --name=nginxpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$nginxnm"
podman run -dt --pod $podsnm --name=gatepod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$gatenm"
podman run -dt --pod $podsnm --name=flowpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$flownm"


