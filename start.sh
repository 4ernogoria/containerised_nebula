#!/bin/bash
read -p 'pods data folder? (default=/data): ' deffold
if [ -z $deffold ]
then deffold=/data
fi
read -p 'mariadb img name? (default=mdb): ' mdbnm
if [ -z $mdbnm ]
then mdbnm=mdb
fi
read -p 'mariadb root passwd? (default=passwd): ' mdbroot
if [ -z $mdbroot ]
then mdbroot=passwd
fi
read -p 'mariadb oneadmin passwd? (default=passwd): ' mdbusr
if [ -z $mdbusr ]
then mdbusr=passwd
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
read -p 'volume for etc files (default=etc)' etcfiles
if [ -z $etcfiles ]
then etcfiles="etc"
fi
read -p 'volume for var files (default=var)' varfiles
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
cd ../

mkdir -p -m 777 "$deffold" "$deffold"/"$logvol"
mkdir -p "$deffold"/"$varfiles"/.one && echo "oneadmin:Sonic2005" > "$deffold"/"$varfiles"/.one/one_auth
mkdir -p "$deffold"/"$etcfiles" && chown -R 9869:9869 "$deffold"/"$etcfiles" "$deffold"/"$varfiles"
mkdir -p "$deffold"/"$mdbvol" && chown -R 27:27 "$deffold"/"$mdbvol"
cd "$deffold"/"$etcfiles" && tar -xvf $currpath/etcdraft.tar
cd "$deffold"/"$varfiles" && tar -xvf $currpath/vardraft.tar

podman pod create --name $podsnm --publish "$podwport":80 --publish "$podvncport":29876
podman run -dt --pod $podsnm --name=mdb -e MYSQL_ROOT_PASSWORD="$mdbroot" -e MYSQL_USER=oneadmin -e MYSQL_PASSWORD="$mdbusr" -e MYSQL_DATABASE=opennebula  -v "$deffold"/"$mdbvol":/var/lib/mysql -v "$deffold"/"$logvol":/var/log/mariadb "$mdbnm"
sleep 5
podman run -dt --pod $podsnm --name=onedpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$onednm"
sleep 5
podman run -dt --pod $podsnm --name=schedpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$schednm"
podman run -dt --pod $podsnm --name=nginxpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$nginxnm"
podman run -dt --pod $podsnm --name=gatepod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$gatenm"
podman run -dt --pod $podsnm --name=flowpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one "$flownm"

#podman run -dt --ip="$mdbip" --name=mariadb -e MYSQL_ROOT_PASSWORD="$mdbroot" -e MYSQL_USER=oneadmin -e MYSQL_PASSWORD="$mdbusr" -e MYSQL_DATABASE=opennebula  -v "$mdbvol":/var/lib/mysql -p $mdbport:3306 "$mdbnm"
#sleep 5
#podman run -dt --ip="$onedip" --name=oned -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -p $onedport:2633 "$onednm"
#sleep 5
#podman run -dt --ip="$nginxip" --name=nginx -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -p "$novncport":29876 -p $nginxport:80 "$nginxnm"
#podman run -dt --ip="$flowip" --name=flow -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one  "$flownm"
#podman run -dt --ip="$gateip" --name=gate -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -p $gateport:5030 "$gatenm"
