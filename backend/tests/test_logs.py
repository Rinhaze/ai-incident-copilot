from app.sample_data import sample_logs

def test_batch_is_idempotent(client):
    payload = {"logs": [entry.model_dump(mode="json") for entry in sample_logs(2)]}
    first = client.post("/api/logs/batch", json=payload)
    second = client.post("/api/logs/batch", json=payload)
    assert first.status_code == 201 and first.json()["accepted"] == 2
    assert second.json()["accepted"] == 0 and second.json()["duplicates"] == 2

def test_invalid_batch_is_not_partially_saved(client):
    payload = {"logs": [sample_logs(1)[0].model_dump(mode="json"), {"external_id": "invalid"}]}
    assert client.post("/api/logs/batch", json=payload).status_code == 422
    # external_id from the otherwise valid entry was not persisted.
    assert client.post("/api/logs", json=sample_logs(1)[0].model_dump(mode="json")).json()["accepted"] == 1

def test_duplicate_in_one_batch_is_idempotent(client):
    entry = sample_logs(1)[0].model_dump(mode="json")
    result = client.post("/api/logs/batch", json={"logs": [entry, entry]})
    assert result.status_code == 201
    assert result.json()["accepted"] == 1 and result.json()["duplicates"] == 1

def test_errors_are_korean_structured(client):
    response = client.post("/api/logs", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["message"] == "입력값을 확인해 주세요."
    assert "input" not in response.json()["error"]["details"][0]

def test_text_and_payload_size_are_bounded(client):
    entry = sample_logs(1)[0].model_dump(mode="json")
    entry["service"] = "   "
    assert client.post("/api/logs", json=entry).status_code == 422
    entry = sample_logs(1)[0].model_dump(mode="json")
    entry["message"] = "x" * 20_001
    assert client.post("/api/logs", json=entry).status_code == 422
    entry = sample_logs(1)[0].model_dump(mode="json")
    entry["attributes"] = {"payload": "x" * 65_536}
    assert client.post("/api/logs", json=entry).status_code == 422
