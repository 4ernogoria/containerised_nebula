#!/bin/bash
read -p "Choose is it necesssary to create the basic configs? (default=No) :" configcrt
#if [ -z $configcrt ]
#then podvncport="Yes"
#fi
read -p 'backup container img name? (default=4ernogoria/backup): ' backnm
if [ -z $backnm ]
then backnm=4ernogoria/backup
fi
#Presence of the check.file in a certain place means that Opennebula hasn't been properly extantiated yet, and during the start of containers it's going to be deployed
#on a predeployed system this file shouldn't exist, or it triggers rewriting of /etc/one and /var/lib/one files 
read -p 'oneadmin default password? (default=Sonic2005): ' onedpass
if [ -z $onedpass ]
then onedpass=Sonic2005
fi
read -p 'pods volume data folder(where the data folders required by containers are stored)? (default=/opt): ' deffold
if [ -z $deffold ]
then deffold=/opt
fi
read -p 'mariadb backup folder, inside the just defined pods volume? (default=mback): ' mbackvol
if [ -z $mbackvol ]
then mbackvol=mback
fi
read -p 'mariadb container img name? (default=4ernogoria/mdb): ' mdbnm
if [ -z $mdbnm ]
then mdbnm=4ernogoria/mdb
fi
read -p 'mariadb root passwd? (default=Sonic2005): ' mdbroot
if [ -z $mdbroot ]
then mdbroot=Sonic2005
fi
read -p 'mariadb oneadmin passwd? (default=Sonic2005): ' mdbusr
if [ -z $mdbusr ]
then mdbusr=Sonic2005
fi
read -p 'mariadb folder to store database into? (default=mysql): ' mdbvol
if [ -z $mdbvol ]
then mdbvol=mysql
fi
read -p 'folder to store logs into? (default=log): ' logvol
if [ -z $logvol ]
then logvol=log
fi
read -p 'base image name? (default=4ernogoria/baseimg): ' basenm
if [ -z $basenm ]
then basenm=4ernogoria/baseimg
fi
read -p 'oned container img name? (default=4ernogoria/baseimg): ' onednm
if [ -z $onednm ]
then onednm=4ernogoria/oned
fi
read -p 'scheduler container img name? (default=4ernogoria/sched): ' schednm
if [ -z $schednm ]
then schednm=4ernogoria/sched
fi
read -p 'nginx container img name? (default=4ernogoria/nginx): ' nginxnm
if [ -z $nginxnm ]
then nginxnm=4ernogoria/nginx
fi
read -p 'flow container img name? (default=4ernogoria/flow): ' flownm
if [ -z $flownm ]
then flownm=4ernogoria/flow
fi
read -p 'gate container img name? (default=4ernogoria/gate): ' gatenm
if [ -z $gatenm ]
then gatenm=4ernogoria/gate
fi
read -p 'folder to store etc/one files into? (default=etc):' etcfiles
if [ -z $etcfiles ]
then etcfiles="etc"
fi
read -p 'volume to store var/lib/one files into? (default=var) :' varfiles
if [ -z $varfiles ]
then varfiles="var"
fi
read -p "the pod's name (default=onepod) :" podsnm
if [ -z $podsnm ]
then podsnm="onepod"
fi
read -p "the pod's web port publised at the host? (default=8080) :" podwport
if [ -z $podwport ]
then podwport="8080"
fi
read -p "the pod's noVNC port publushed at the host? (default=29876) :" podvncport
if [ -z $podvncport ]
then podvncport="29876"
fi

currpath=$(/bin/pwd)

setenforce 0
sed 's/SELINUX=disabled/SELINUX=disabled/' /etc/selinux/config
## needed for user root to connect to db
#echo -e "[client] \nuser=root \npassword='mdbroot'" > /root/.my.cnf && chmod 400 /root/.my.cnf

if [ -d "$deffold" ] #folder containing all the data of Opeenebula and MariaDB plus logging and logic triggers
then
        echo "main folder exists, proceed"
else
	mkdir /opt
#        echo "the folder does not exist, check if the volume mounted correctly" | logger
	exit
fi

#if [ -f /opt/log/check.file ] ## the file, if created, by mdbbackup container shows the need to instatiate a prestart configuration  
if [ -z $configcrt ]
	then
		echo "you've chosen not to create configs"
	else
#Creates a folder tree, which was required during the installation step on testing phase
#uid 9869 is one used by user in the containers, therefore folders must have right permissions, and user is being created.
#This step also creates one_auth file, which in a main one defining oneadmin credentials.
#Copies main Opennebula configs and /var/lib/one directory stucture

#        	echo "the /opt/log/check.file has been found, preconfiguration is required" 2>&1 | logger
        	mkdir -p "$deffold"/"$logvol" "$deffold"/"$varfiles" "$deffold"/"$etcfiles" "$deffold"/"$mdbvol" "$deffold"/"$varfiles"/.one "$deffold"/"$mbackvol" 2>&1 | logger
        	chown -R 9869:9869 "$deffold" "$deffold"/"$logvol" "$deffold"/"$varfiles" "$deffold"/"$etcfiles" "$deffold"/"$mdbvol" "$deffold"/"$varfiles"/.one "$deffold"/"$mbackvol"
        	chmod 770 "$deffold" "$deffold"/"$logvol" "$deffold"/"$varfiles" "$deffold"/"$etcfiles" "$deffold"/"$mdbvol" "$deffold"/"$varfiles"/.one "$deffold"/"$mbackvol"
        	echo "oneadmin:$onedpass" > "$deffold"/"$varfiles"/.one/one_auth
        	useradd -u 9869 -M -s /sbin/nologin oneadmin 2>&1 | logger
        	cd "$deffold"/"$etcfiles" && tar -xvf $currpath/etcdraft.tar 2>&1 | logger
        	cd "$deffold"/"$varfiles" && tar -xvf $currpath/vardraft.tar 2>&1 | logger
        	chown -R 9869:9869 "$deffold"/"$etcfiles" "$deffold"/"$varfiles"
#else
#	echo "file has not been found, no need to do anything, just start containers" 2>&1 | logger
fi


#stage creates a pod the containers themselves, had no need to publish any more port since everything else communicates through localhost tcp sockets
podman pod create --name $podsnm --publish "$podwport":80 --publish "$podvncport":29876
podman run -dt --pod $podsnm --name=mdb -e MYSQL_ROOT_PASSWORD="$mdbroot" -e MYSQL_USER=oneadmin -e MYSQL_PASSWORD="$mdbusr" -e MYSQL_DATABASE=opennebula -v "$deffold"/"$mdbvol":/var/lib/mysql -v "$deffold"/"$logvol":/var/log/mariadb -v /etc/localtime:/etc/localtime:ro "$mdbnm"
sleep 5
#/var/log/mariadb folder is a place for the check.file  which presence triggers the config deployment; /opt/var folder is checked during the pod start to figure it's current state, deployed or not (contains
#/var/lib/one/.one files explicitly, along with the mysql querry, showing the current state); For some reason mariabackup demands DB folder to be mounted backing container (seems to me it uses a fileoriented way backup), also
#it requires /xtrabackup_files folder be created and having write permission into it in the current folder of your position, so you have to define folder as a working directory as the exact the same place you've mounted backup
#volume to; /opt/mysql/backup - mounting path also is used at the backup container as a path target to use during mariadb backup and a working directory in the Dockerfile, so if changed here, be aware!
podman run -dt --pod $podsnm --name=mbackup -v "$deffold"/"$mdbvol":/var/lib/mysql -v "$deffold"/"$logfiles":/var/log/mariadb -v "$deffold"/"$mbackvol":/opt/mysql/backup -v "$deffold"/"$varfiles":/opt/var "$backnm"
sleep 5
podman run -dt --pod $podsnm --name=onedpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one -v /etc/localtime:/etc/localtime:ro "$onednm"
sleep 5
podman run -dt --pod $podsnm --name=schedpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one -v /etc/localtime:/etc/localtime:ro "$schednm"
podman run -dt --pod $podsnm --name=nginxpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one -v /etc/localtime:/etc/localtime:ro "$nginxnm"
podman run -dt --pod $podsnm --name=gatepod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one -v /etc/localtime:/etc/localtime:ro "$gatenm"
podman run -dt --pod $podsnm --name=flowpod -v "$deffold"/"$etcfiles":/etc/one  -v "$deffold"/"$varfiles":/var/lib/one -v "$deffold"/"$logvol":/var/log/one -v /etc/localtime:/etc/localtime:ro "$flownm"


