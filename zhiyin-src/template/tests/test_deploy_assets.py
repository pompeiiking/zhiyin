from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEPLOY = REPO_ROOT / "deploy"


def test_compose_includes_wanwu_and_keeps_zhiyin_internal() -> None:
    text = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
    assert "zhiyin-api:" in text
    assert "expose:" in text and '"8000"' in text
    assert "wanwu-net" in text
    assert "condition: service_healthy" in text
    for service in ("mysql", "redis", "minio", "kafka", "es", "bff-service", "agentscope", "rag", "agent"):
        assert f"  {service}:\n    ports: !reset []" in text
    assert '"127.0.0.1:8081:8081"' in text
    assert "context: ../../zhiyin-src/template" in text
    assert "- ../../deploy/.env" in text
    assert "KAFKA_CFG_ADVERTISED_LISTENERS: BROKER://${WANWU_KAFKA_HOST}:9092" in text
    assert 'test: ["CMD", "redis-cli", "-a", "${WANWU_REDIS_PASSWORD}", "ping"]' in text
    assert "zhiyin-web:" in text
    assert '"127.0.0.1:8080:8080"' in text
    assert "dockerfile: Dockerfile.web" in text


def test_zhiyin_web_image_serves_spa_and_proxies_api() -> None:
    dockerfile = (REPO_ROOT / "zhiyin-src" / "template" / "Dockerfile.web").read_text(
        encoding="utf-8"
    )
    nginx = (
        REPO_ROOT
        / "zhiyin-src"
        / "template"
        / "zhiyin-web"
        / "nginx.conf"
    ).read_text(encoding="utf-8")
    assert "npm run build" in dockerfile
    assert "FROM nginx:1.27-alpine" in dockerfile
    assert "try_files $uri $uri/ /index.html" in nginx
    assert "location /api/v1/" in nginx
    assert "proxy_pass http://zhiyin-api:8000" in nginx


def test_mysql_runtime_includes_rsa_auth_dependency() -> None:
    pyproject = (REPO_ROOT / "zhiyin-src" / "template" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert pyproject.count('"cryptography>=42,<47"') == 2


def test_env_example_has_no_committed_secrets() -> None:
    text = (DEPLOY / ".env.example").read_text(encoding="utf-8")
    assert "WANWU_PROJECT_DIR=../../deploy/runtime\n" in text
    assert "WANWU_ELASTIC_ADDRESS=es-wanwu:9200\n" in text
    for key in (
        "WANWU_MYSQL_PASSWORD",
        "WANWU_REDIS_PASSWORD",
        "WANWU_MINIO_PASSWORD",
        "WANWU_ELASTIC_PASSWORD",
    ):
        assert f"{key}=\n" in text


def test_lifecycle_scripts_do_not_delete_volumes() -> None:
    down = (DEPLOY / "down.ps1").read_text(encoding="utf-8")
    assert " down" in down
    assert "--volumes" not in down
    assert " -v" not in down
    up = (DEPLOY / "up.ps1").read_text(encoding="utf-8")
    assert "'--project-directory', $WanwuRoot" in up
    for name in ("down.ps1", "verify.ps1"):
        text = (DEPLOY / name).read_text(encoding="utf-8")
        assert "--project-directory $WanwuRoot" in text


def test_ci_renders_compose_from_the_wanwu_project_directory() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "docker compose --project-directory platform/wanwu" in ci


def test_ci_installs_m3_dependencies_before_collecting_full_suite() -> None:
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert 'pip install -e ".[dev,m3]"' in ci


def test_init_env_generates_passwords_without_changing_public_values() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("init_env", DEPLOY / "init_env.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rendered = module.build_environment("PUBLIC=value\nDB_PASSWORD=\n")
    assert "PUBLIC=value" in rendered
    assert "DB_PASSWORD=\n" not in rendered


def test_ai_config_script_prompts_for_secret_without_printing_it() -> None:
    text = (DEPLOY / "set-ai-config.ps1").read_text(encoding="utf-8")
    assert "Read-Host 'OpenAI-compatible API key' -AsSecureString" in text
    assert "WANWU_EMBEDDING_DIMENSION = '1024'" in text
    assert "the API key was not printed" in text


def test_service_smoke_creates_and_cleans_real_business_objects() -> None:
    probe = (
        REPO_ROOT
        / "zhiyin-src"
        / "template"
        / "scripts"
        / "verify_wanwu_business.py"
    ).read_text(encoding="utf-8")
    runner = (DEPLOY / "test-all.ps1").read_text(encoding="utf-8")
    for service in (
        "iam-service",
        "model-service",
        "mcp-service",
        "knowledge-service",
        "rag-service",
        "assistant-service",
        "app-service",
        "agentscope",
        "elasticsearch",
        "zhiyin-api/zhiyin-web",
    ):
        assert service in probe
    assert "finally:" in probe and "self.cleanup()" in probe
    assert "verify_wanwu_business.py" in runner
    assert "real-object-create/read/update/delete/cleanup" in runner
