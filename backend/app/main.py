from __future__ import annotations
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
import asyncio
import json
import os
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, get_session, initialize_database
from .logs import ingest_logs
from .models import Incident, IncidentLog, IncidentStatus, NormalizedLog, OutboxEvent, StatusHistory
from .schemas import IncidentDetail, IncidentSummary, LogBatchInput, LogIngestResult, LogInput, StatusChange
from .summary import build_rule_summary, summarize_with_optional_codex

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database(engine)
    yield

app = FastAPI(title="AI Incident Copilot", version="0.2.0", lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in error.get("loc", ())),
            "type": str(error.get("type", "invalid")),
            "message": "입력값을 확인해 주세요.",
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "요청 형식이 올바르지 않습니다.", "details": details}})

@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": "REQUEST_ERROR", "message": str(exc.detail)}})

@app.exception_handler(Exception)
async def internal_error(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "서버에서 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."}})

@app.get("/health")
def health() -> dict[str, str]: return {"status": "ok", "instance": os.getenv("APP_INSTANCE_ID", "default")}

@app.post("/api/logs", response_model=LogIngestResult, status_code=201)
def ingest_one(item: LogInput, session: Annotated[Session, Depends(get_session)]) -> LogIngestResult:
    return _ingest(session, [item])

@app.post("/api/logs/batch", response_model=LogIngestResult, status_code=201)
def ingest_batch(payload: LogBatchInput, session: Annotated[Session, Depends(get_session)]) -> LogIngestResult:
    return _ingest(session, payload.logs)

def _ingest(session: Session, logs: list[LogInput]) -> LogIngestResult:
    try:
        records, duplicates = ingest_logs(session, logs); session.commit()
        return LogIngestResult(accepted=len(records), duplicates=duplicates, ids=[r.id for r in records])
    except Exception:
        session.rollback(); raise

@app.get("/api/incidents", response_model=list[IncidentSummary])
def list_incidents(session: Annotated[Session, Depends(get_session)], service: str | None = None, severity: str | None = None, status: str | None = None, from_at: datetime | None = Query(None, alias="from"), to: datetime | None = None) -> list[Incident]:
    query = select(Incident).order_by(Incident.opened_at.desc())
    if service: query = query.where(Incident.service == service)
    if severity: query = query.where(Incident.severity == severity)
    if status: query = query.where(Incident.status == status)
    if from_at: query = query.where(Incident.opened_at >= from_at)
    if to: query = query.where(Incident.opened_at <= to)
    return list(session.scalars(query).all())

def detail(incident: Incident, session: Session) -> IncidentDetail:
    logs = session.execute(select(NormalizedLog).join(IncidentLog, IncidentLog.log_id == NormalizedLog.id).where(IncidentLog.incident_id == incident.id).order_by(NormalizedLog.timestamp)).scalars().all()
    history = session.scalars(select(StatusHistory).where(StatusHistory.incident_id == incident.id).order_by(StatusHistory.created_at)).all()
    log_values = [{"id": str(log.id), "timestamp": log.timestamp, "severity": log.severity, "message": log.message, "trace_id": log.trace_id} for log in logs]
    rule_summary = build_rule_summary(incident, logs)
    analysis = summarize_with_optional_codex(rule_summary, log_values)
    return IncidentDetail(id=incident.id, fingerprint=incident.fingerprint, service=incident.service, severity=incident.severity, title=incident.title, status=incident.status, opened_at=incident.opened_at, updated_at=incident.updated_at, resolved_at=incident.resolved_at, logs=log_values, timeline=[{"type": "status", "from": row.from_status, "to": row.to_status, "at": row.created_at, "actor": row.actor} for row in history], analysis=analysis)

@app.get("/api/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: UUID, session: Annotated[Session, Depends(get_session)]) -> IncidentDetail:
    incident = session.get(Incident, incident_id)
    if not incident: raise HTTPException(404, "incident를 찾을 수 없습니다.")
    return detail(incident, session)

@app.patch("/api/incidents/{incident_id}/status", response_model=IncidentSummary)
def change_status(incident_id: UUID, body: StatusChange, session: Annotated[Session, Depends(get_session)]) -> Incident:
    incident = session.get(Incident, incident_id)
    if not incident: raise HTTPException(404, "incident를 찾을 수 없습니다.")
    valid = {"open": {"acknowledged"}, "acknowledged": {"resolved"}, "resolved": set()}
    if body.status not in valid[incident.status]: raise HTTPException(409, f"{incident.status} 상태에서는 {body.status}(으)로 변경할 수 없습니다.")
    before = incident.status; incident.status = body.status
    if body.status == "resolved": incident.resolved_at = datetime.now(timezone.utc)
    session.add(StatusHistory(incident_id=incident.id, from_status=before, to_status=body.status, actor=body.actor))
    session.add(OutboxEvent(topic="incident.status_changed", aggregate_id=str(incident.id), dedupe_key=f"status:{incident.id}:{before}:{body.status}", payload={"incident_id": str(incident.id), "from": before, "to": body.status}))
    session.commit(); session.refresh(incident); return incident

@app.get("/api/events")
async def events(request: Request, cursor: int | None = Query(None, ge=0)) -> StreamingResponse:
    header = request.headers.get("last-event-id")
    try: after = int(header) if header is not None else (cursor or 0)
    except ValueError: raise HTTPException(400, "Last-Event-ID는 0 이상의 정수여야 합니다.")
    if after < 0: raise HTTPException(400, "cursor는 0 이상의 정수여야 합니다.")
    heartbeat = max(1.0, float(os.getenv("SSE_HEARTBEAT_SECONDS", "15")))
    async def stream():
        nonlocal after
        last_heartbeat = asyncio.get_running_loop().time()
        while not await request.is_disconnected():
            with SessionLocal() as db:
                rows = db.scalars(select(OutboxEvent).where(OutboxEvent.sequence > after).order_by(OutboxEvent.sequence).limit(100)).all()
            if rows:
                for event in rows:
                    after = event.sequence
                    data = {"topic": event.topic, "aggregate_id": event.aggregate_id, "payload": event.payload, "created_at": event.created_at.isoformat()}
                    yield f"id: {event.sequence}\nevent: {event.topic}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                last_heartbeat = asyncio.get_running_loop().time()
                continue
            now = asyncio.get_running_loop().time()
            if now - last_heartbeat >= heartbeat:
                yield ": heartbeat\n\n"; last_heartbeat = now
            await asyncio.sleep(min(0.25, heartbeat))
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
