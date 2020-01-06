# containerised_nebula

  Basically, it works like:
add the execution bit to start.sh; start it from the cloned directory. It's gonna ask you a number of questions, generate images: 
- MariaDB10.4 presetted DB's settings;
- Baseimage(containing OpenNebula's 5.10 all necessary components);
- Oned/scheduler/flow/gate images having the baseimg as a foundation, just starting a particular service above;
- Nginx+Passanger+sunstone image, baseimg based, but with additional pieces of software included;
  
  Starts up a POD with a number of binded ports (inside NGINX, noVNC).

  Creates folders for the MariaDB database, logs, /etc/one, /var/lib/one.
  
  Starts up all the needed containers inside the POD, communicating one another through network ports on shared LOCALHOST, with apropriately mounted volumes.
 !!!During the nebula installtion ssh keys had been created, and later moved to /temp/var.  Need to add something Baseimg: create a script /script.sh (containing #!/bin/bash \n cp -rf /temp/var/.ssh /var/lib/one/), make it executable; add a string in the basic start.sh, right before starting the pod, need to run a container based on baseimg with a mounted folder /opt/var:/var/lib/one, and run /script.sh inside it as an entrypoint, this will copy ssh keys at the apropriate places and close itself by the script finish.
