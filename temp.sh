#!/bin/bash
read -p 'mdb vol? (default=mysql): ' mdbvol
if [ -z $mdbvol ]
then mdbvol=mysql
fi
read -p 'pods data folder? (default=/var/nebulapod): ' deffold
if [ -z $deffold ]
then deffold=/var/nebulapod
fi
read -p 'log volume? (default=log): ' logvol
if [ -z $logvol ]
then logvol=log
fi
read -p 'volume for etc files (default=etc)' etcfiles
if [ -z $etcfiles ]
then etcfiles="etc"
fi
read -p 'volume for var files (default=var)' varfiles
if [ -z $varfiles ]
then varfiles="var"
fi
fullbasenm=localhost/"$basenm"
currpath=$(/bin/pwd)
mkdir -p -m 777 "$deffold" "$deffold"/"$logvol"
mkdir -p "$deffold"/"$varfiles"/.one && echo "oneadmin:Sonic2005" > "$deffold"/"$varfiles"/.one/one_auth
mkdir -p "$deffold"/"$etcfiles" && chown -R 9869:9869 "$deffold"/"$etcfiles" "$deffold"/"$varfiles"
mkdir -p "$deffold"/"$mdbvol" && chown 27:27 "$deffold"/"$mdbvol"
cd "$deffold"/"$etcfiles" && tar -xvf $currpath/etc_v10.tar
cd "$deffold"/"$varfiles" && tar -xvf $currpath/var_v10.tar
#podman pod create --name $podsnm --publish "$podwport":80 --publish "$podvncport":29876
#podman run -dt --pod $podsnm --name=mdb -e MYSQL_ROOT_PASSWORD="$mdbroot" -e MYSQL_USER=oneadmin -e MYSQL_PASSWORD="$mdbusr" -e MYSQL_DATABASE=opennebula  -v "$mdbvol":/var/lib/mysql -v "$logvol":/var/log/mariadb "$mdbnm"
#sleep 5
#podman run -dt --pod $podsnm --name=onedpod -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -v "$logvol":/var/log/one "$onednm"
#sleep 5
#podman run -dt --pod $podsnm --name=schedpod -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -v "$logvol":/var/log/one "$schednm"
#podman run -dt --pod $podsnm --name=nginxpod -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -v "$logvol":/var/log/one "$nginxnm"
#podman run -dt --pod $podsnm --name=gatepod -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -v "$logvol":/var/log/one "$gatenm"
#podman run -dt --pod $podsnm --name=flowpod -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -v "$logvol":/var/log/one "$flownm"
#podman run -dt --ip="$mdbip" --name=mariadb -e MYSQL_ROOT_PASSWORD="$mdbroot" -e MYSQL_USER=oneadmin -e MYSQL_PASSWORD="$mdbusr" -e MYSQL_DATABASE=opennebula  -v "$mdbvol":/var/lib/mysql -p $mdbport:3306 "$mdbnm"
#sleep 5
#podman run -dt --ip="$onedip" --name=oned -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -p $onedport:2633 "$onednm"
#sleep 5
#podman run -dt --ip="$nginxip" --name=nginx -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -p "$novncport":29876 -p $nginxport:80 "$nginxnm"
#podman run -dt --ip="$flowip" --name=flow -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one  "$flownm"
#podman run -dt --ip="$gateip" --name=gate -v "$logfiles":/var/log/one -v "$etcfiles":/etc/one  -v "$varfiles":/var/lib/one -p $gateport:5030 "$gatenm"
