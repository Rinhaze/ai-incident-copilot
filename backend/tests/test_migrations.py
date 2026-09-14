from pathlib import Path
from sqlalchemy import create_engine, text
from app.database import SQLITE_SCHEMA_VERSION, initialize_database
from app.models import OutboxEvent
from sqlalchemy.orm import Session

def test_legacy_sqlite_is_migrated_once_without_data_loss(tmp_path: Path):
    database = tmp_path / "legacy.db"
    target = create_engine(f"sqlite:///{database}")
    with target.begin() as c:
        c.execute(text("CREATE TABLE outbox_events (id CHAR(32) PRIMARY KEY NOT NULL, topic VARCHAR(128) NOT NULL, aggregate_id VARCHAR(36) NOT NULL, payload JSON NOT NULL, created_at DATETIME NOT NULL)"))
        c.execute(text("CREATE TABLE detection_records (id CHAR(32) PRIMARY KEY NOT NULL, incident_id CHAR(32), kind VARCHAR(64) NOT NULL, payload JSON NOT NULL, created_at DATETIME NOT NULL)"))
        c.execute(text("INSERT INTO outbox_events VALUES ('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','legacy.topic','agg',:payload,'2025-01-01 00:00:00')"),{"payload":'{"kept":true}'})
        c.execute(text("INSERT INTO detection_records VALUES ('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',NULL,'legacy',:payload,'2025-01-01 00:00:00')"),{"payload":'{"kept":true}'})
    initialize_database(target)
    initialize_database(target)
    with target.connect() as c:
        outbox=c.execute(text("SELECT id,sequence,dedupe_key,payload FROM outbox_events")).one()
        detection=c.execute(text("SELECT id,dedupe_key,payload FROM detection_records")).one()
        versions=c.scalar(text("SELECT count(*) FROM schema_migrations WHERE version=:v"),{"v":SQLITE_SCHEMA_VERSION})
    assert outbox[0]=="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" and outbox[1]==1 and outbox[2].startswith("legacy:outbox:") and "kept" in outbox[3]
    assert detection[0]=="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" and detection[1].startswith("legacy:detection:") and "kept" in detection[2]
    assert versions==1
    with Session(target) as session:
        session.add(OutboxEvent(topic="현재.topic",aggregate_id="agg",dedupe_key="current",payload={"ok":True}));session.commit()
        assert session.query(OutboxEvent).filter_by(dedupe_key="current").one().sequence==2
