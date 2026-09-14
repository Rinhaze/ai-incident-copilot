from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> dict:
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def test_default_compose_contract():
    compose = load("docker-compose.yml")
    assert set(compose["services"]) == {"api", "frontend"}
    assert compose["services"]["api"]["environment"]["DATABASE_URL"].startswith("sqlite:")
    assert compose["services"]["frontend"]["depends_on"]["api"]["condition"] == "service_healthy"
    assert "incident-data" in compose["volumes"]


def test_postgres_override_contract():
    compose = load("docker-compose.postgres.yml")
    postgres = compose["services"]["postgres"]
    assert postgres["image"].startswith("postgres:16")
    assert "postgresql+psycopg://" in compose["services"]["api"]["environment"]["DATABASE_URL"]
    assert postgres["healthcheck"]["test"][0] == "CMD-SHELL"


def test_ci_runs_compose_restart_smoke():
    workflow = (ROOT / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")
    smoke = (ROOT / "scripts" / "compose_smoke.py").read_text(encoding="utf-8")
    assert "python scripts/compose_smoke.py" in workflow
    assert 'run("restart", "api")' in smoke
    assert '"--volumes", "--remove-orphans"' in smoke
