# 문제 해결 기록

## 1. 값만 다른 오류를 같은 장애로 묶기

### 문제

주문 ID, UUID, IP가 매번 바뀌는 같은 오류가 서로 다른 로그처럼 보여 운영자가 반복 검색해야 했습니다.

### 원인과 제약

원문 전체 hash는 동적 값에 민감합니다. 반대로 숫자를 무조건 제거하면 의미 있는 상태 코드까지 합쳐질 수 있습니다. MVP는 로그 parser를 서비스마다 만드는 대신 일반적인 동적 패턴을 제한적으로 다루기로 했습니다.

### 구현

UUID, IPv4·포트, 긴 16진수, 단독 숫자와 경로의 동적 segment를 placeholder로 바꿉니다. `service + normalized_message`의 SHA-256을 fingerprint로 사용하고 `error`·`critical`만 incident에 연결했습니다.

### 검증

값이 다른 두 메시지가 같은 fingerprint를 만드는 단위 테스트, 한 batch 안 중복과 재수집 멱등성 테스트, 세 로그가 하나의 incident와 하나의 급증 detection을 만드는 통합 테스트를 실행했습니다.

### 결과와 배움

결정론적 grouping이 AI 없이도 재현됩니다. 서비스별 로그 문법이 달라질 때는 일반 정규식을 계속 늘리기보다 parser plugin과 보존된 normalized field를 비교하는 방식이 필요합니다.

## 2. 단위 테스트가 놓친 기존 DB 회귀

### 문제

첫 Edge E2E에서 `outbox_events has no column named dedupe_key`와 `no such column: sequence`로 API가 500을 반환했습니다.

### 원인과 제약

단위 테스트는 매번 현재 모델로 새 in-memory DB를 만들었습니다. 개발 중 생성된 SQLite에는 구 schema가 남아 있었고 SQLAlchemy `create_all()`은 기존 테이블을 변경하지 않았습니다. DB 파일 삭제는 실제 사용자 데이터를 잃으므로 해결책에서 제외했습니다.

### 구현

startup lifespan에서 schema version을 확인하고, legacy outbox 데이터를 새 sequence 기반 테이블로 복사하는 migration을 만들었습니다. detection/outbox dedupe key도 기존 ID에서 안정적으로 채웠습니다.

### 검증

구 schema와 샘플 데이터를 직접 만든 뒤 migration을 두 번 실행하는 테스트를 추가했습니다. 기존 행 보존, sequence 부여, 새 event의 다음 sequence, migration version 1건을 확인했습니다. 이후 동일 Edge E2E가 통과했습니다.

### 결과와 배움

신규 DB 테스트만으로 schema 변경을 검증할 수 없다는 점을 확인했습니다. 다음 단계에서는 Alembic과 업그레이드·다운그레이드 정책을 도입해야 합니다.

## 3. E2E 실패 뒤 서버가 남는 문제

### 문제

초기 Playwright 실패 후 8000·5173 포트가 계속 점유되어 다음 테스트가 서버 준비 timeout으로 실패했습니다.

### 원인과 제약

global setup이 실패하면 global teardown이 실행되지 않을 수 있고, Windows에서 부모 `kill()`만 호출하면 Python·Node 자식이 남았습니다.

### 구현

setup 단계가 backend instance ID까지 확인하도록 하고, 실패 시 `taskkill /T /F`로 해당 자식 트리만 정리합니다. 각 실행은 UUID 이름의 SQLite를 사용하며 정상 teardown에서 서버 PID, DB, 상태 파일을 제거합니다.

### 검증

잔여 PID를 실행 시각·실행 파일과 포트로 확인해 정리한 뒤 E2E를 반복 실행했습니다. 테스트 종료 후 8000·5173에 LISTENING socket이 남지 않음을 확인했습니다.

### 결과와 배움

E2E는 화면 assertion뿐 아니라 격리된 상태와 종료 보장까지 포함해야 반복 가능한 검증이 됩니다.

## 4. AI 설명과 원본 근거 분리

### 문제

자유 형식 AI 요약은 입력에 없는 원인을 단정하거나 존재하지 않는 log ID를 인용할 수 있습니다.

### 원인과 제약

로그 자체가 prompt injection 문자열을 포함할 수 있고 CLI 로그인·한도·격리 상태도 언제든 달라질 수 있습니다. 외부 유료 API fallback은 사용할 수 없습니다.

### 구현

규칙 요약을 기본으로 두고 AI 입력을 제한된 evidence JSON으로 만들었습니다. ChatGPT 로그인, Windows read-deny readiness, strict output schema, 출력 크기, timeout, source, 인용 ID subset을 검사합니다. API key 관련 환경변수는 자식 프로세스에서 제거합니다.

### 검증

가짜 실행기로 argv·stdin·`shell=False`·schema·환경변수 제거를 확인하고, API key 로그인·허위 인용·timeout을 각각 규칙 요약 fallback으로 돌리는 부정 테스트를 실행했습니다. 실제 Codex 요약은 현재 하위 CLI가 로그인되지 않아 미검증입니다.

### 결과와 배움

AI는 탐지와 저장의 진실 원본이 아니라 검증을 통과해야 하는 선택적 설명 계층으로 두는 편이 장애 대응 도구에 적합했습니다.
