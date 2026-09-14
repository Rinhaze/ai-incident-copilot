from __future__ import annotations
from datetime import datetime, timedelta, timezone
import argparse
from sqlalchemy import select
from .database import SessionLocal, engine, initialize_database
from .logs import ingest_logs
from .models import Incident
from .schemas import LogInput

def sample_logs(count: int = 20, seed: int = 0) -> list[LogInput]:
    """Deterministic fixtures suitable for a demo or repeatable test."""
    base = datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seed)
    return [LogInput(external_id=f"sample-{seed}-{i}", service=("payments" if i % 2 else "orders"), severity=("error" if i % 3 else "warning"), message=f"sample failure #{i}", timestamp=base + timedelta(minutes=i), attributes={"sample": True, "sequence": i}) for i in range(count)]

def sample_incident_logs(seed: int = 0) -> list[LogInput]:
    """동적 주문 ID와 IP가 달라도 같은 결제 장애로 묶이는 재현 시나리오."""
    base = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc) + timedelta(seconds=seed)
    return [LogInput(external_id=f"payment-outage-{seed}-{i}", service="payments", severity=("critical" if i == 2 else "error"), message=f"POST /orders/{4100+i}/capture failed from 10.20.0.{10+i} request 550e8400-e29b-41d4-a716-44665544000{i}", timestamp=base + timedelta(seconds=i * 20), attributes={"scenario": "payment-db-timeout", "seed": seed}) for i in range(3)]

def seed_demo(seed: int = 0) -> dict[str, int]:
    initialize_database(engine)
    with SessionLocal() as session:
        created, duplicates = ingest_logs(session, sample_incident_logs(seed))
        session.commit()
        incidents = len(session.scalars(select(Incident)).all())
    return {"accepted": len(created), "duplicates": duplicates, "incidents": incidents}

def main() -> None:
    parser = argparse.ArgumentParser(description="스크린샷용 결제 장애 데모 데이터를 저장합니다.")
    parser.add_argument("--seed", type=int, default=0, help="같은 값으로 다시 실행하면 중복 저장되지 않습니다.")
    args = parser.parse_args()
    result = seed_demo(args.seed)
    print(f"데모 데이터 준비 완료: 신규 로그 {result['accepted']}건, 중복 {result['duplicates']}건, 전체 장애 {result['incidents']}건")

if __name__ == "__main__":
    main()
