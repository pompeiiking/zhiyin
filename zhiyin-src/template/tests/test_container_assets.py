from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_backend_dockerfile_runs_as_non_root_and_uses_healthz() -> None:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.11-slim" in text
    assert "USER zhiyin" in text
    assert '"--host", "0.0.0.0"' in text
    assert "/healthz" in text
    assert 'CMD ["python", "-m", "zhiyin_boot"' in text


def test_dockerignore_excludes_secrets_and_generated_files() -> None:
    lines = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())
    assert {".env", ".env.*", ".git", ".venv", "**/__pycache__", "zhiyin-web/node_modules"} <= lines
