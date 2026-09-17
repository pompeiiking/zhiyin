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
    for name in ("up.ps1", "down.ps1", "verify.ps1"):
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
