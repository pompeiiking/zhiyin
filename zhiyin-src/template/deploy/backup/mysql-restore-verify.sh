#!/bin/sh
set -eu
latest="$(find /backups/mysql -type f -name 'zhiyin_service-*.sql.gz' | sort | tail -n 1)"
test -n "${latest}"
verify_db="zhiyin_restore_verify"
mysql -h "${MYSQL_HOST}" -u root -e "DROP DATABASE IF EXISTS ${verify_db}; CREATE DATABASE ${verify_db} CHARACTER SET utf8mb4;"
gzip -dc "${latest}" | mysql -h "${MYSQL_HOST}" -u root "${verify_db}"
count="$(mysql -N -h "${MYSQL_HOST}" -u root -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${verify_db}';")"
test "${count}" -gt 0
mysql -h "${MYSQL_HOST}" -u root -e "DROP DATABASE ${verify_db};"
echo "restore_verify_ok=${latest} tables=${count}"
