from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.database import get_session
from app.logs import fingerprint, normalize_message
from app.models import DetectionRecord, Incident, IncidentLog, OutboxEvent

def item(external_id, at, message="GET /users/123 failed from 10.0.0.8 request 550e8400-e29b-41d4-a716-446655440000"):
    return {"external_id":external_id,"service":"api","severity":"error","message":message,"timestamp":at.isoformat()}

def test_dynamic_values_have_stable_fingerprint():
    a=normalize_message("/users/123 10.0.0.8 550e8400-e29b-41d4-a716-446655440000 0xabcdef123456")
    b=normalize_message("/users/999 192.168.1.1 123e4567-e89b-42d3-a456-426614174000 0x111111111111")
    assert a==b
    assert fingerprint("api",a)==fingerprint("api",b)

def test_ingest_groups_and_detects_once_across_reingest(client, monkeypatch):
    monkeypatch.setenv("DETECTION_THRESHOLD","3");monkeypatch.setenv("DETECTION_WINDOW_SECONDS","60")
    base=datetime(2025,1,1,tzinfo=timezone.utc); payload={"logs":[item(str(i),base+timedelta(seconds=i*10)) for i in range(3)]}
    assert client.post("/api/logs/batch",json=payload).json()["accepted"]==3
    assert client.post("/api/logs/batch",json=payload).json()["duplicates"]==3
    session=next(client.app.dependency_overrides[get_session]())
    assert len(session.scalars(select(Incident)).all())==1
    assert len(session.scalars(select(IncidentLog)).all())==3
    assert len(session.scalars(select(DetectionRecord)).all())==1
    assert len(session.scalars(select(OutboxEvent).where(OutboxEvent.topic=="incident.spike_detected")).all())==1
    session.close()

def test_window_boundary_is_inclusive(client,monkeypatch):
    monkeypatch.setenv("DETECTION_THRESHOLD","2");monkeypatch.setenv("DETECTION_WINDOW_SECONDS","60")
    base=datetime(2025,1,1,tzinfo=timezone.utc)
    client.post("/api/logs/batch",json={"logs":[item("a",base),item("b",base+timedelta(seconds=60))]})
    session=next(client.app.dependency_overrides[get_session]()); assert len(session.scalars(select(DetectionRecord)).all())==1;session.close()
