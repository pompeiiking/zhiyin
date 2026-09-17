#!/bin/sh
set -eu
latest="$(find /backups/pgvector -type f -name 'zhiyin_vector-*.dump' | sort | tail -n 1)"
test -n "${latest}"
verify_db="zhiyin_restore_verify"
dropdb --if-exists -h "${PGHOST}" -U "${PGUSER}" "${verify_db}"
createdb -h "${PGHOST}" -U "${PGUSER}" "${verify_db}"
pg_restore -h "${PGHOST}" -U "${PGUSER}" -d "${verify_db}" "${latest}"
count="$(psql -At -h "${PGHOST}" -U "${PGUSER}" -d "${verify_db}" -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")"
test "${count}" -gt 0
dropdb -h "${PGHOST}" -U "${PGUSER}" "${verify_db}"
echo "restore_verify_ok=${latest} tables=${count}"
