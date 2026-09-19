FROM postgres:16

# 使用 PostgreSQL 官方 APT 源提供的 pgvector 0.8.x。基础镜像和扩展版本都可锁定，
# 避免部署环境的 Docker Hub 镜像代理不可用时无法完成 M3 初始化。
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector=0.8.6-1.pgdg13+1 \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/zhiyin-postgres-entrypoint.sh
RUN chmod 0755 /usr/local/bin/zhiyin-postgres-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/zhiyin-postgres-entrypoint.sh"]
