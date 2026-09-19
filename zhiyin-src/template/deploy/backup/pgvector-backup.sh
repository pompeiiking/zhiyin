#!/bin/sh
set -eu
umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="/backups/pgvector/zhiyin_vector-${stamp}.dump"
mkdir -p /backups/pgvector
pg_dump -Fc -h "${PGHOST}" -U "${PGUSER}" -d "${PGDATABASE}" -f "${target}"
pg_restore --list "${target}" >/dev/null
find /backups/pgvector -type f -name 'zhiyin_vector-*.dump' -mtime +7 -delete
echo "backup_ok=${target}"
