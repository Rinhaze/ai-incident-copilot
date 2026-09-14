from sqlalchemy import select
from app.database import get_session
from app.models import OutboxEvent

def test_outbox_sequence_is_ordered_and_resume_cursor_is_exclusive(client):
    session=next(client.app.dependency_overrides[get_session]())
    session.add_all([OutboxEvent(topic="a",aggregate_id="1",dedupe_key="a",payload={}),OutboxEvent(topic="b",aggregate_id="2",dedupe_key="b",payload={})]);session.commit()
    rows=session.scalars(select(OutboxEvent).order_by(OutboxEvent.sequence)).all();cursor=rows[0].sequence
    resumed=session.scalars(select(OutboxEvent).where(OutboxEvent.sequence>cursor).order_by(OutboxEvent.sequence)).all()
    assert [x.topic for x in rows]==["a","b"] and [x.topic for x in resumed]==["b"]
    session.close()

def test_sse_rejects_invalid_last_event_id(client):
    response=client.get('/api/events',headers={'Last-Event-ID':'invalid'})
    assert response.status_code==400 and '정수' in response.json()['error']['message']
