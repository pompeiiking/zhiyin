#!/bin/sh
set -eu

# 独立 WAL 卷不是 PGDATA 的子目录，官方 entrypoint 不会自动修正它的属主。
# 首次挂载的 Docker volume 默认为 root:root，必须在降权到 postgres 前处理。
if [ "$(id -u)" = "0" ]; then
    mkdir -p /var/lib/postgresql/wal_archive
    chown postgres:postgres /var/lib/postgresql/wal_archive
    chmod 0700 /var/lib/postgresql/wal_archive
fi

exec docker-entrypoint.sh "$@"
