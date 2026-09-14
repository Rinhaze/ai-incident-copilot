# API 사용법

기본 주소는 `http://127.0.0.1:8000`입니다. Swagger UI는 `/docs`, OpenAPI JSON은 `/openapi.json`에서 확인합니다.

## 로그 1건 수집

```http
POST /api/logs
Content-Type: application/json

{
  "external_id": "payment-20250101-001",
  "service": "payments",
  "severity": "critical",
  "message": "POST /orders/4101/capture failed from 10.20.0.11",
  "timestamp": "2025-01-01T09:00:00Z",
  "trace_id": "trace-demo-001",
  "attributes": {"scenario": "payment-db-timeout"}
}
```

성공 응답은 신규·중복 수와 저장된 log ID를 돌려줍니다. 같은 `external_id`를 다시 보내면 `accepted=0`, `duplicates=1`입니다.

## 여러 로그 수집

`POST /api/logs/batch`의 body는 `{"logs": [...]}`이며 한 요청에 1~1,000건을 받습니다. batch 안 한 항목이라도 schema가 틀리면 422로 거부되고 저장은 시작되지 않습니다.

## incident 검색

```http
GET /api/incidents?service=payments&severity=critical&status=open&from=2025-01-01T00:00:00Z&to=2025-01-02T00:00:00Z
```

모든 query는 선택입니다. 상세 조회 `GET /api/incidents/{incident_id}`는 로그, 상태 타임라인, 규칙 또는 Codex 분석을 함께 반환합니다.

## 상태 변경

```http
PATCH /api/incidents/{incident_id}/status
Content-Type: application/json

{"status":"acknowledged","actor":"dashboard"}
```

허용 흐름은 `open → acknowledged → resolved`입니다. 해결된 fingerprint에 새 오류가 들어오면 detector가 `resolved → open` 이력을 남기고 재개합니다.

## 실시간 event

```http
GET /api/events?cursor=0
Accept: text/event-stream
```

각 event에는 정수 `id`, topic 이름, JSON data가 있습니다. 재연결할 때 `Last-Event-ID`를 보내거나 `cursor`를 지정하면 그 다음 sequence부터 받습니다.

## 오류 형식

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "요청 형식이 올바르지 않습니다.",
    "details": [{"field": "body.service", "type": "value_error", "message": "입력값을 확인해 주세요."}]
  }
}
```

입력 원문과 내부 예외 객체는 오류 응답에 되돌려 주지 않습니다.
