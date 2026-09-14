"""임시 SQLite에서 API 로그 수집 경로를 재현 측정한다."""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="개발 환경의 로그 수집 회귀 성능을 측정합니다.")
    parser.add_argument("--count", type=int, default=1_000, choices=range(1, 1_001), metavar="1..1000")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="incident-benchmark-") as temp:
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(temp, 'benchmark.db').as_posix()}"
        os.environ["CODEX_SUMMARY_ENABLED"] = "false"
        from fastapi.testclient import TestClient
        from app.database import engine
        from app.main import app

        base = datetime(2025, 1, 1, tzinfo=UTC)
        logs = [
            {
                "external_id": f"benchmark-{index}",
                "service": "payments",
                "severity": "error",
                "message": f"POST /orders/{10_000 + index}/capture failed from 10.0.0.{index % 250 + 1}",
                "timestamp": (base + timedelta(milliseconds=index)).isoformat(),
                "attributes": {"benchmark": True},
            }
            for index in range(args.count)
        ]
        with TestClient(app) as client:
            started = time.perf_counter()
            response = client.post("/api/logs/batch", json={"logs": logs})
            elapsed = time.perf_counter() - started
            response.raise_for_status()
            incidents = client.get("/api/incidents").json()
        engine.dispose()

    result = {
        "measured_at": datetime.now(UTC).isoformat(),
        "scope": "단일 프로세스 TestClient + 임시 SQLite 개발 환경 회귀 측정",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "log_count": args.count,
        "incident_count": len(incidents),
        "elapsed_ms": round(elapsed * 1_000, 2),
        "logs_per_second": round(args.count / elapsed, 2),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
