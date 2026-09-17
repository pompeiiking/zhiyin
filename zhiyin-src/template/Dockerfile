FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system zhiyin && useradd --system --gid zhiyin --home-dir /app zhiyin

COPY pyproject.toml README.md ./
COPY zhiyin-kernel ./zhiyin-kernel
COPY zhiyin-api ./zhiyin-api
COPY zhiyin-business ./zhiyin-business
COPY zhiyin-orchestration ./zhiyin-orchestration
COPY zhiyin-data-sdk ./zhiyin-data-sdk
COPY zhiyin-infrastructure ./zhiyin-infrastructure
COPY zhiyin-boot ./zhiyin-boot
COPY data ./data
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

RUN python -m pip install ".[m3]" && chown -R zhiyin:zhiyin /app
COPY --chown=zhiyin:zhiyin scripts ./scripts

USER zhiyin
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=12 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["python", "-m", "zhiyin_boot", "--host", "0.0.0.0", "--port", "8000"]
