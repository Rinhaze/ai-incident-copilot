"""Database configuration kept deliberately separate from API code."""
from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def database_url() -> str:
    """Return configured URL, defaulting to a project-local SQLite database."""
    return os.getenv("DATABASE_URL", "sqlite:///./data/incidents.db")


def make_engine(url: str | None = None) -> Engine:
    url = url or database_url()
    options: dict[str, object] = {"future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" not in url:
            # SQLite relative database location; PostgreSQL needs no path handling.
            db_part = url.removeprefix("sqlite:///")
            if db_part and not db_part.startswith("/"):
                Path(db_part).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, **options)


class Base(DeclarativeBase):
    pass


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

SQLITE_SCHEMA_VERSION = "20260914_01_outbox_sequence_dedupe"

def initialize_database(target: Engine = engine) -> None:
    """신규 schema를 만들고 기존 SQLite scaffold를 데이터 보존 방식으로 한 번만 올린다."""
    Base.metadata.create_all(target)
    if target.dialect.name != "sqlite":
        return
    with target.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(128) PRIMARY KEY, applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        done = connection.scalar(text("SELECT 1 FROM schema_migrations WHERE version=:version"), {"version": SQLITE_SCHEMA_VERSION})
        if done:
            return
        tables = set(inspect(connection).get_table_names())
        if "detection_records" in tables:
            detection_columns = {row["name"] for row in inspect(connection).get_columns("detection_records")}
            if "dedupe_key" not in detection_columns:
                connection.execute(text("ALTER TABLE detection_records ADD COLUMN dedupe_key VARCHAR(255)"))
                connection.execute(text("UPDATE detection_records SET dedupe_key='legacy:detection:' || id WHERE dedupe_key IS NULL"))
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_detection_dedupe ON detection_records(dedupe_key)"))
        if "outbox_events" in tables:
            outbox_columns = {row["name"] for row in inspect(connection).get_columns("outbox_events")}
            if "sequence" not in outbox_columns or "dedupe_key" not in outbox_columns:
                connection.execute(text("ALTER TABLE outbox_events RENAME TO outbox_events_legacy"))
                connection.execute(text("CREATE TABLE outbox_events (sequence INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, id CHAR(32) NOT NULL UNIQUE, dedupe_key VARCHAR(255) NOT NULL UNIQUE, topic VARCHAR(128) NOT NULL, aggregate_id VARCHAR(36) NOT NULL, payload JSON NOT NULL, created_at DATETIME NOT NULL)"))
                connection.execute(text("INSERT INTO outbox_events(id,dedupe_key,topic,aggregate_id,payload,created_at) SELECT id,'legacy:outbox:' || id,topic,aggregate_id,payload,created_at FROM outbox_events_legacy ORDER BY created_at,id"))
                connection.execute(text("DROP TABLE outbox_events_legacy"))
                connection.execute(text("CREATE INDEX ix_outbox_events_created ON outbox_events(created_at)"))
                connection.execute(text("CREATE INDEX ix_outbox_events_id ON outbox_events(id)"))
                connection.execute(text("CREATE INDEX ix_outbox_events_topic ON outbox_events(topic)"))
                connection.execute(text("CREATE INDEX ix_outbox_events_aggregate_id ON outbox_events(aggregate_id)"))
        connection.execute(text("INSERT INTO schema_migrations(version) VALUES (:version)"), {"version": SQLITE_SCHEMA_VERSION})


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
