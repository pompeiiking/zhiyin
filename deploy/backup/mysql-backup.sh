#!/bin/sh
set -eu
umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="/backups/mysql/zhiyin_service-${stamp}.sql.gz"
plain="${target%.gz}"
mkdir -p /backups/mysql
trap 'rm -f "${plain}" "${target}.tmp"' EXIT
mysqldump --single-transaction --routines --triggers --set-gtid-purged=OFF \
  --no-tablespaces -h "${MYSQL_HOST}" -u "${MYSQL_USER}" "${MYSQL_DATABASE}" > "${plain}"
gzip -9 "${plain}"
gzip -t "${target}"
find /backups/mysql -type f -name 'zhiyin_service-*.sql.gz' -mtime +7 -delete
echo "backup_ok=${target}"
