# containerised_nebula

Whats been changed:
1) changed the backup system. Now it may work on centos as well as alpine linuxes. For Centos there has been rebuilded a cron package which rid of the PAM dependencies, and works perfecrly correct now(need to check how it's got terminated though).
2) Changed a way the sched container works(In NEbula 5.10 they rewrite the mm_ched code, and now it starts in foreground by default) which doesnt require any auxiliary scripts to get terminated correctly
3) The nginx now gets terminated smoothly. Were added to the entrypoint "exec" starting starting nginx itself, and STOPSIGNAL SIGTERM to the Dockerfile
