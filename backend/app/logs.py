"""결정론적 로그 정규화, incident 그룹화와 급증 탐지."""
from __future__ import annotations
import hashlib
import os
import re
from datetime import timedelta
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import DetectionRecord, Incident, IncidentLog, IncidentStatus, NormalizedLog, OutboxEvent, StatusHistory
from .schemas import LogInput

UUID_RE = re.compile(r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-f])", re.I)
IP_RE = re.compile(r"(?<![\d.])(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?::\d{1,5})?(?![\d.])")
HEX_RE = re.compile(r"(?<![\w])(?:0x)?[0-9a-f]{10,}(?![\w])", re.I)
PATH_RE = re.compile(r"(?P<prefix>(?:[A-Za-z]:)?[/\\])(?P<body>[^\s?'\"]+)")
NUMBER_RE = re.compile(r"(?<![\w.])-?\d+(?![\w.])")

def _normalize_path(match: re.Match[str]) -> str:
    parts = re.split(r"[/\\]+", match.group("body"))
    stable = []
    for part in parts:
        if UUID_RE.fullmatch(part) or HEX_RE.fullmatch(part) or re.fullmatch(r"\d+", part): stable.append("{id}")
        else: stable.append(part)
    return "/" + "/".join(stable)

def normalize_message(message: str) -> str:
    value = UUID_RE.sub("{uuid}", message)
    value = IP_RE.sub("{ip}", value)
    value = PATH_RE.sub(_normalize_path, value)
    value = HEX_RE.sub("{hex}", value)
    value = NUMBER_RE.sub("{id}", value)
    return re.sub(r"\s+", " ", value.strip())

def fingerprint(service: str, normalized_message: str) -> str:
    return hashlib.sha256(f"{service.strip()}\n{normalized_message}".encode("utf-8")).hexdigest()

def _group_and_detect(session: Session, record: NormalizedLog) -> None:
    if record.severity not in {"error", "critical"}: return
    incident = session.scalar(select(Incident).where(Incident.fingerprint == record.fingerprint))
    if incident is None:
        incident = Incident(fingerprint=record.fingerprint, service=record.service, severity=record.severity, title=record.message[:500], opened_at=record.timestamp)
        session.add(incident); session.flush()
        session.add(StatusHistory(incident_id=incident.id, from_status=None, to_status="open", actor="system"))
        session.add(OutboxEvent(topic="incident.created", aggregate_id=str(incident.id), dedupe_key=f"incident:{incident.id}:created", payload={"incident_id": str(incident.id)}))
    else:
        if incident.status == IncidentStatus.RESOLVED.value:
            incident.status = IncidentStatus.OPEN.value
            incident.resolved_at = None
            session.add(StatusHistory(incident_id=incident.id, from_status="resolved", to_status="open", actor="detector"))
            session.add(OutboxEvent(topic="incident.reopened", aggregate_id=str(incident.id), dedupe_key=f"incident:{incident.id}:reopened:{record.id}", payload={"incident_id": str(incident.id), "log_id": str(record.id)}))
        if record.severity == "critical": incident.severity = "critical"
    session.add(IncidentLog(incident_id=incident.id, log_id=record.id))
    window_seconds = max(1, int(os.getenv("DETECTION_WINDOW_SECONDS", "300")))
    threshold = max(1, int(os.getenv("DETECTION_THRESHOLD", "3")))
    start = record.timestamp - timedelta(seconds=window_seconds)
    count = session.query(NormalizedLog).filter(NormalizedLog.fingerprint == record.fingerprint, NormalizedLog.timestamp >= start, NormalizedLog.timestamp <= record.timestamp, NormalizedLog.severity.in_(("error", "critical"))).count()
    # 고정 epoch bucket은 경계와 재시작에도 동일한 dedupe key를 만든다.
    bucket = int(record.timestamp.timestamp()) // window_seconds
    key = f"spike:{record.fingerprint}:{bucket}"
    if count >= threshold and not session.scalar(select(DetectionRecord.id).where(DetectionRecord.dedupe_key == key)):
        detection = DetectionRecord(incident_id=incident.id, kind="fingerprint_spike", dedupe_key=key, payload={"count": count, "threshold": threshold, "window_seconds": window_seconds, "window_end": record.timestamp.isoformat()})
        session.add(detection)
        session.add(OutboxEvent(topic="incident.spike_detected", aggregate_id=str(incident.id), dedupe_key=key, payload={"incident_id": str(incident.id), "count": count, "threshold": threshold}))

def ingest_logs(session: Session, logs: Sequence[LogInput]) -> tuple[list[NormalizedLog], int]:
    external_ids = [log.external_id for log in logs]
    seen = set(session.scalars(select(NormalizedLog.external_id).where(NormalizedLog.external_id.in_(external_ids))).all())
    created: list[NormalizedLog] = []
    # 입력 배열 순서와 무관하게 같은 결과가 나오도록 event time과 external id로 고정 정렬한다.
    for item in sorted(logs, key=lambda value: (value.timestamp, value.external_id)):
        if item.external_id in seen: continue
        normalized = normalize_message(item.message)
        service = item.service.strip()
        record = NormalizedLog(external_id=item.external_id, service=service, severity=item.severity, message=item.message.strip(), timestamp=item.timestamp, trace_id=item.trace_id, fingerprint=fingerprint(service, normalized), attributes={**item.attributes, "normalized_message": normalized})
        session.add(record); session.flush(); created.append(record); seen.add(item.external_id)
        _group_and_detect(session, record)
    session.flush()
    return created, len(logs) - len(created)
