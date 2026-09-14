# 면접 설명 자료

## 30초 소개

AI Incident Copilot은 여러 서비스의 JSON 로그를 같은 장애 단위로 묶고, 급증과 발생 흐름, 원인 후보, 대응 체크리스트를 한 화면에서 확인하는 운영 대시보드입니다. Python/FastAPI와 React/TypeScript로 만들었고 SQLite를 기본으로, PostgreSQL을 선택할 수 있게 구성했습니다. AI가 없어도 결정론적 fingerprint와 규칙 요약으로 전체 기능이 동작하며, 선택적 Codex 결과는 원본 log ID 인용과 strict schema를 통과해야 표시됩니다.

## 제가 보여주고 싶은 역량

- API·DB·React 화면을 한 저장소에서 연결한 백엔드·풀스택 기본기
- 재수집, 재시작, SSE 재연결을 고려한 멱등성과 복구 설계
- AI 출력을 신뢰하지 않고 schema·근거·fallback으로 검증한 도구 활용 방식
- 단위 테스트만 믿지 않고 실제 Edge E2E와 dependency audit에서 문제를 찾고 수정한 과정

## 기술 선택 이유

**왜 FastAPI와 SQLAlchemy인가요?**
JSON 입력 schema와 한국어 오류를 Pydantic으로 명확히 만들고 SQLite·PostgreSQL 저장 계층을 같은 모델로 다루기 위해 선택했습니다. 비동기 처리가 핵심인 시스템은 아니어서 DB 처리는 단순한 동기 Session으로 유지했고 SSE loop만 async로 분리했습니다.

**왜 SQLite가 기본인가요?**
채용 담당자가 별도 인프라 없이 데모를 재현할 수 있기 때문입니다. 높은 동시 쓰기는 목표가 아니며 그 한계를 문서에 명시했습니다. PostgreSQL Compose는 선택 경로로 두었지만 현재 환경에서 live 검증하지 않았습니다.

**왜 WebSocket이 아니라 SSE인가요?**
브라우저가 서버 event를 받는 단방향 요구가 중심입니다. HTTP 기반 자동 재연결과 `Last-Event-ID`를 활용할 수 있어 MVP가 단순해집니다. 상태 변경은 일반 PATCH API로 분리했습니다.

## 깊게 설명할 문제 해결

### 기존 DB에서는 왜 E2E가 실패했나요?

단위 테스트가 매번 현재 모델로 새 DB를 만들어 schema 변경 문제를 가렸습니다. 실제 개발 DB에는 outbox의 `sequence`와 `dedupe_key`가 없었고 `create_all()`은 기존 테이블을 변경하지 않습니다. DB 삭제 대신 versioned migration으로 legacy 행을 새 테이블에 복사했고, migration을 두 번 실행해도 데이터와 sequence가 유지되는 테스트를 추가했습니다.

### 테스트 뒤 포트가 남은 문제는 어떻게 해결했나요?

Playwright global setup 실패 시 teardown이 보장되지 않았고 Windows 부모 프로세스만 종료해서 자식 uvicorn/Vite가 남았습니다. instance ID가 맞는 서버만 준비 완료로 인정하고, 실패 시 기록된 프로젝트 PID의 자식 트리를 정리하도록 바꿨습니다. 이후 E2E 종료 뒤 8000·5173 LISTENING socket이 없는지 확인했습니다.

### AI가 틀린 원인을 쓰면 어떻게 하나요?

AI는 incident 생성이나 severity 결정에 관여하지 않습니다. 규칙 결과가 항상 먼저 있고, Codex에는 제한된 로그 evidence만 전달합니다. 결과가 strict schema를 어기거나 입력에 없는 log ID를 인용하면 폐기하고 규칙 요약을 보여줍니다. API key fallback도 두지 않았습니다.

### 개발 중 중단된 검증은 어떻게 복구했나요?

E2E 실행이 중단된 뒤 남아 있던 서버 프로세스와 사용 중인 포트를 확인하고 종료했습니다. 각 E2E 실행마다 별도의 SQLite 파일을 사용하도록 격리한 뒤 같은 시나리오를 다시 실행해 통과 여부를 확인했습니다. setup 실패 경로에서도 자식 프로세스가 남지 않도록 종료 처리를 보강했습니다.

## 검증 근거

2026-09-15 기준 pytest 23개, Vitest 3개, 설치된 Microsoft Edge Playwright E2E 1개와 Vite production build를 실행했습니다. `pip-audit`와 `npm audit`는 알려진 취약점 0개를 보고했습니다. 첫 audit에서 pytest·Starlette 취약점을 발견해 FastAPI 생태계 호환 버전으로 올린 뒤 전체 회귀를 다시 실행했습니다.

Docker·PostgreSQL·제품 내 Codex live 요약은 현재 환경 조건을 충족하지 않아 미검증입니다. 이 범위를 배포 성공이나 live 성공으로 설명하지 않습니다.

## 예상 후속 질문

**동시 수집이 많아지면 무엇을 바꾸겠습니까?**
PostgreSQL로 전환하고 fingerprint incident 생성과 dedupe를 database upsert로 묶겠습니다. 여러 API 인스턴스가 SSE outbox를 소비하면 polling worker와 보존·ack 정책을 분리하겠습니다.

**정규식 fingerprint의 오탐은 어떻게 줄이겠습니까?**
원본과 normalized message를 함께 보존하고 서비스별 parser version을 fingerprint 입력에 포함하겠습니다. 샘플 replay로 이전/신규 parser의 병합·분리 변화를 비교한 뒤 version을 올리겠습니다.

**다음 개선 우선순위는 무엇인가요?**
Alembic migration, PostgreSQL 통합 테스트, outbox 보존 정책과 관측 지표, 서비스별 parser plugin 순서입니다. 인증·멀티테넌시는 실제 배포 요구가 생겼을 때 별도 threat model과 함께 설계하겠습니다.
