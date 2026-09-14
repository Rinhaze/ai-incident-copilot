from app.database import get_session
from app.models import Incident, StatusHistory
from app.sample_data import sample_incident_logs

def seed_incident(client):
    session = next(client.app.dependency_overrides[get_session]())
    incident = Incident(fingerprint="fp-test", service="orders", severity="error", title="주문 오류")
    session.add(incident); session.flush()
    session.add(StatusHistory(incident_id=incident.id, from_status=None, to_status="open")); session.commit()
    value = str(incident.id); session.close(); return value

def test_list_search_detail_and_state_transition(client):
    incident_id = seed_incident(client)
    assert len(client.get("/api/incidents?service=orders&severity=error").json()) == 1
    assert client.get(f"/api/incidents/{incident_id}").status_code == 200
    assert client.patch(f"/api/incidents/{incident_id}/status", json={"status": "acknowledged"}).status_code == 200
    assert client.patch(f"/api/incidents/{incident_id}/status", json={"status": "resolved"}).json()["status"] == "resolved"
    assert client.patch(f"/api/incidents/{incident_id}/status", json={"status": "acknowledged"}).status_code == 409

def test_resolved_incident_is_reopened_by_new_matching_error(client):
    logs = sample_incident_logs(10)
    first = logs[0].model_dump(mode="json")
    assert client.post("/api/logs", json=first).status_code == 201
    incident_id = client.get("/api/incidents").json()[0]["id"]
    client.patch(f"/api/incidents/{incident_id}/status", json={"status": "acknowledged"})
    client.patch(f"/api/incidents/{incident_id}/status", json={"status": "resolved"})
    assert client.post("/api/logs", json=logs[1].model_dump(mode="json")).status_code == 201
    detail = client.get(f"/api/incidents/{incident_id}").json()
    assert detail["status"] == "open" and detail["resolved_at"] is None
    assert [row["to"] for row in detail["timeline"]][-1] == "open"
