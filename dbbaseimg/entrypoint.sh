#!/bin/bash
set -e

if [ "${1:0:1}" = '-' ]; then # extracts the first simbol of the very first argument if its "-"
	set -- mysqld_safe "$@" # set the argument to mysql_safe list_of_arguments
fi

if [ "$1" = 'mysqld_safe' ]; then # if the previous one went OK
	DATADIR="/var/lib/mysql"
	
	if [ ! -d "$DATADIR/mysql" ]; then # if there is no mysql folder in DATADIR consider database not created yet, going to create
		if [ -z "$MYSQL_ROOT_PASSWORD" -a -z "$MYSQL_ALLOW_EMPTY_PASSWORD" ]; then # checks if mysql_root_pass and allow_epmty_password not defined
			echo >&2 'error: database is uninitialized and MYSQL_ROOT_PASSWORD not set'
			echo >&2 '  Did you forget to add -e MYSQL_ROOT_PASSWORD=... ?'
			exit 1
		fi
		
		echo 'Running mysql_install_db ...' # no databases were created yet
		mysql_install_db --force --datadir="$DATADIR"
		echo 'Finished mysql_install_db'
		
		# These statements _must_ be on individual lines, and _must_ end with
		# semicolons (no line breaks or comments are permitted).
		# TODO proper SQL escaping on ALL the things D:
		
		tempSqlFile='/tmp/mysql-first-time.sql'
		cat > "$tempSqlFile" <<-EOSQL
			DELETE FROM mysql.user ;
			CREATE USER 'root'@'%' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}' ;
			GRANT ALL ON *.* TO 'root'@'%' WITH GRANT OPTION ;
			DROP DATABASE IF EXISTS test ;
		EOSQL
		
		if [ "$MYSQL_DATABASE" ]; then # ifdefined mysql_database create it if not yet
			echo "CREATE DATABASE IF NOT EXISTS \`$MYSQL_DATABASE\` ;" >> "$tempSqlFile"
			if [ "$MYSQL_CHARSET" ]; then
				echo "ALTER DATABASE \`$MYSQL_DATABASE\` CHARACTER SET \`$MYSQL_CHARSET\` ;" >> "$tempSqlFile"
			fi
			
			if [ "$MYSQL_COLLATION" ]; then
				echo "ALTER DATABASE \`$MYSQL_DATABASE\` COLLATE \`$MYSQL_COLLATION\` ;" >> "$tempSqlFile"
			fi
		fi
		
		if [ "$MYSQL_USER" -a "$MYSQL_PASSWORD" ]; then #if defined a mysql_user and his password make him the owner
			echo "CREATE USER '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWORD' ;" >> "$tempSqlFile"
			
			if [ "$MYSQL_DATABASE" ]; then
				echo "GRANT ALL ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%';" >> "$tempSqlFile"
				echo "GRANT select,reload,process ON *.* TO '$MYSQL_USER'@'%';" >> "$tempSqlFile"
			fi
		fi
		
		echo 'FLUSH PRIVILEGES ;' >> "$tempSqlFile"
		
		set -- "$@" --init-file="$tempSqlFile"
	fi
	
fi

exec "$@"
