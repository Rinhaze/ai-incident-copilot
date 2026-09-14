# 구현 계획

AI 없이도 로그 수집부터 장애 그룹화·급증 탐지·상태 관리·근거 기반 요약까지 동작하는 AI Incident Copilot MVP를 구현한다. 선택적 Codex CLI 요약은 결정론적 분석과 분리하고 schema 및 근거 인용을 검증한다.

## 아키텍처

backend는 Python 3.12/FastAPI의 API 계층, 순수 함수 기반 정규화·fingerprint·탐지 계층, SQLAlchemy 저장 계층으로 구성한다. SQLite 파일을 기본 저장소로 사용하고 DATABASE_URL과 DB 접근 계층을 분리한다. 로그·incident·상태 이력·탐지 결과·이벤트를 트랜잭션으로 저장한다. MVP는 단일 API 프로세스로 실행하며, 영속 이벤트 테이블을 조회하는 SSE로 재연결과 누락 복구를 지원한다. frontend는 React/TypeScript/Vite로 구현하고 Vitest·React Testing Library·Playwright를 보조 검증 도구로 사용한다. 규칙 기반 요약은 항상 제공하며, Codex CLI는 기본 비활성화된 어댑터에서만 호출한다. 모든 아래 검증 명령과 테스트 경로는 구현 전 확정할 계약이며 각 작업에서 해당 테스트·스크립트를 함께 작성한다. Docker Compose와 CI의 필수 검증은 AI 인증이나 유료 API 없이 실행된다.

## 작업

- T001: 프로젝트 골격과 검증 실행 환경
- T002: 데이터 모델과 저장 계약
- T003: JSON 로그 수집과 재현 데이터
- T004: fingerprint 장애 그룹화
- T005: 시간창 급증 탐지
- T006: incident 조회·검색·상태·타임라인 API
- T007: 복구 가능한 실시간 이벤트 스트림
- T008: 근거 기반 규칙 요약과 체크리스트
- T009: 선택적 Codex CLI 요약 어댑터
- T010: incident 목록과 검색 UI
- T011: 상세·타임라인·요약·실시간 UI
- T012: Docker Compose 실행과 복구 smoke
- T013: 핵심 사용자 흐름 E2E
- T014: CI와 전체 Git 이력 secret scan
- T015: 재현 가능한 성능 측정과 포트폴리오 문서
