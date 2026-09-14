# 검증 기록

## 2026-09-15 로컬 검증

| 구분 | 명령 | 실제 결과 |
|---|---|---|
| Backend | `.venv\Scripts\python.exe -m pytest -q` | 23 passed |
| Frontend | `npm test -- --run` | 3 passed |
| Build | `npm run build` | Vite production build 성공 |
| Browser E2E | `npx playwright test --config playwright.config.ts` | 설치된 Microsoft Edge에서 1 passed |
| Python 보안 | `python -m pip_audit -r requirements.txt` | known vulnerability 0개 |
| npm 보안 | `npm audit --json` | vulnerability 0개 |
| 종료 상태 | 테스트 후 8000·5173 LISTENING 확인 | 잔여 listener 없음 |
| 개발 회귀 측정 | `benchmark.py --count 1000` | 1,097.15ms, 911.45 logs/s |

최종 commit 뒤 Git tree, working tree, 전체 Git object의 secret·개인정보 검사와 원격 SHA 대조를 수행했습니다. 이 파일에는 자기 자신을 포함한 commit SHA를 하드코딩하지 않습니다.

## 부정·복구 시나리오

- batch 한 항목이 잘못되면 전체 요청 422, 정상 항목도 저장하지 않음
- 같은 external ID 재수집과 같은 시간 bucket detection 중복 방지
- 구 SQLite outbox/detection schema를 두 번 migration해도 데이터와 version 유지
- 해결된 incident에 동일 fingerprint 새 오류가 오면 상태 이력과 함께 재개
- 잘못된 SSE `Last-Event-ID` 거부, sequence cursor 다음 event부터 조회
- Codex API key 로그인·허위 log ID·timeout·출력 문제 시 규칙 요약 fallback
- E2E마다 UUID SQLite 사용, 정상·setup 실패 때 프로젝트 서버 자식 트리 정리

## 모의 검증과 live 검증 구분

선택적 Codex 어댑터의 argv, stdin, 환경변수 제거, strict schema, timeout, 인용 검사는 fake runner로 검증했습니다. 현재 실행 환경에서는 하위 Codex CLI의 `login status`가 `Not logged in`이고 Windows read-deny 조건도 충족하지 않아 제품의 live incident 요약은 실행하지 않았습니다. 기본 규칙 기반 요약과 fallback 경로는 독립 테스트로 검증했습니다.

## 미검증 범위

- 현재 PC에 Docker가 없어 Compose build·health smoke 미실행
- PostgreSQL 선택 구성의 실제 DB 연결·migration 미실행
- 프록시를 둔 장시간 SSE heartbeat·재연결 운영 시험 미실행
- 인증, 멀티테넌시, 클라우드 배포는 MVP 범위 밖

도구 없음, 네트워크 오류, 테스트 0개는 통과로 처리하지 않습니다.

성능 값은 Python 3.12.14, Windows 10, 단일 프로세스 TestClient와 임시 SQLite에서 2026-09-15에 한 번 측정한 개발 회귀 기준입니다. 네트워크·동시 사용자·운영 DB 성능을 나타내지 않습니다.
