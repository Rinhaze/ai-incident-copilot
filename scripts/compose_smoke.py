from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = f"incident-copilot-smoke-{uuid.uuid4().hex[:10]}"
COMPOSE = ["docker", "compose", "-p", PROJECT, "-f", str(ROOT / "docker-compose.yml")]
BASE_URL = "http://127.0.0.1:5173"


def run(*arguments: str, timeout: int = 300) -> None:
    result = subprocess.run(
        [*COMPOSE, *arguments], cwd=ROOT, shell=False, timeout=timeout,
        text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError(f"docker compose {' '.join(arguments)} 실패(종료 코드 {result.returncode})")


def request(path: str, payload: dict | None = None, timeout: int = 5) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    with urllib.request.urlopen(urllib.request.Request(BASE_URL + path, data=body, headers=headers), timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_until_ready() -> None:
    last_error: Exception | None = None
    for _ in range(60):
        try:
            if request("/health").get("status") == "ok":
                return
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            last_error = error
        time.sleep(1)
    raise RuntimeError(f"Compose 서비스가 준비되지 않았습니다: {last_error}")


def main() -> int:
    external_id = f"compose-{uuid.uuid4()}"
    payload = {
        "logs": [{
            "external_id": external_id,
            "service": "compose-smoke",
            "severity": "error",
            "message": "database connection failed for request 4812",
            "timestamp": "2026-09-15T00:00:00Z",
            "attributes": {"scenario": "compose-restart"},
        }]
    }
    try:
        run("up", "-d", "--build", timeout=600)
        wait_until_ready()
        accepted = request("/api/logs/batch", payload)
        if accepted.get("accepted") != 1:
            raise RuntimeError(f"샘플 로그 수집 결과가 예상과 다릅니다: {accepted}")
        before = request("/api/incidents?service=compose-smoke")
        if len(before) != 1:
            raise RuntimeError("재시작 전 incident를 조회할 수 없습니다")
        run("restart", "api")
        wait_until_ready()
        after = request("/api/incidents?service=compose-smoke")
        if len(after) != 1 or after[0]["id"] != before[0]["id"]:
            raise RuntimeError("API 재시작 뒤 SQLite volume 데이터가 보존되지 않았습니다")
        print("Compose 빌드·수집·재시작 데이터 보존 smoke를 통과했습니다.")
        return 0
    except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError, urllib.error.URLError) as error:
        print(f"Compose smoke 실패: {error}", file=sys.stderr)
        return 1
    finally:
        try:
            subprocess.run(
                [*COMPOSE, "down", "--volumes", "--remove-orphans"], cwd=ROOT,
                shell=False, timeout=120, check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass


if __name__ == "__main__":
    raise SystemExit(main())
