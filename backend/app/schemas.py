from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
import json
from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_SEVERITIES = {"debug", "info", "warning", "error", "critical"}

class LogInput(BaseModel):
    external_id: str = Field(min_length=1, max_length=255)
    service: str = Field(min_length=1, max_length=128)
    severity: str
    message: str = Field(min_length=1, max_length=20_000)
    timestamp: datetime
    trace_id: str | None = Field(default=None, max_length=255)
    attributes: dict[str, Any] = Field(default_factory=dict)
    @field_validator("external_id", "service", "message", "trace_id")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("문자열 값은 공백만 입력할 수 없습니다")
        return value
    @field_validator("attributes")
    @classmethod
    def bounded_attributes(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")) > 65_536:
            raise ValueError("attributes는 UTF-8 기준 64 KiB 이하여야 합니다")
        return value
    @field_validator("severity")
    @classmethod
    def severity_valid(cls, value: str) -> str:
        value = value.lower()
        if value not in VALID_SEVERITIES: raise ValueError("severity는 debug, info, warning, error, critical 중 하나여야 합니다")
        return value
    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None: raise ValueError("timestamp에는 시간대가 필요합니다")
        return value.astimezone(timezone.utc)

class LogBatchInput(BaseModel):
    logs: list[LogInput] = Field(min_length=1, max_length=1000)

class LogIngestResult(BaseModel):
    accepted: int
    duplicates: int
    ids: list[UUID]

class IncidentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; service: str; severity: str; title: str; status: str; opened_at: datetime; updated_at: datetime; resolved_at: datetime | None

class IncidentDetail(IncidentSummary):
    fingerprint: str
    logs: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    analysis: dict[str, Any]

class StatusChange(BaseModel):
    status: str
    actor: str = Field(default="api", max_length=128)
    @field_validator("status")
    @classmethod
    def known_status(cls, value: str) -> str:
        if value not in {"acknowledged", "resolved"}: raise ValueError("status는 acknowledged 또는 resolved여야 합니다")
        return value
