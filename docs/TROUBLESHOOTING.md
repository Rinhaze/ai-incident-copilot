# 트러블슈팅

## 8000 또는 5173 포트를 사용할 수 없음

`WinError 10048`은 다른 프로세스가 포트를 사용 중이라는 뜻입니다.

```powershell
netstat -ano | Select-String ':8000|:5173'
```

PID와 실행 파일을 확인한 뒤 이 프로젝트에서 시작한 프로세스만 종료합니다. 다른 앱의 Node·Python·Edge 프로세스를 일괄 종료하지 않습니다.

## `no such column` 또는 `has no column named` SQLite 오류

현재 버전은 startup에서 초기 scaffold DB를 보존 migration합니다. API를 한 번 정상 시작한 뒤 다시 확인합니다. DB 파일을 바로 삭제하지 마세요. migration 테스트는 `backend/tests/test_migrations.py`에 있습니다.

## Playwright가 서버 준비 실패로 종료됨

- backend `.venv`가 있는지 확인합니다.
- CI나 별도 Python을 쓰면 `E2E_PYTHON=python`을 설정합니다.
- 포트 점유를 확인합니다.
- `.e2e-state/servers.json`이 남았다면 기록된 PID가 실제 이 프로젝트 프로세스인지 확인한 후 정리합니다.

## Codex 요약 대신 규칙 요약이 표시됨

기본 동작입니다. Codex 기능은 OFF이며 ChatGPT 로그인, `CODEX_EXECUTABLE`, Windows read-deny 준비 상태가 모두 필요합니다. 로그인 실패·한도·timeout·schema 오류·허위 인용이 있으면 규칙 요약과 한국어 오류를 표시합니다. API key로 우회하지 않습니다.

## Docker 명령을 찾을 수 없음

Docker Desktop 또는 호환 Docker Compose 환경이 필요합니다. 설치하지 않은 환경에서는 로컬 Python·Node 실행을 사용합니다. 이 저장소는 Docker 미설치 상태를 Compose 성공으로 기록하지 않습니다.

## 의존성 감사가 네트워크 오류로 실패함

`pip-audit`와 `npm audit`는 외부 advisory registry에 접속합니다. 네트워크 실패는 0건이 아니라 검사 실패입니다. 연결이 가능한 환경에서 다시 실행해야 보안 Gate를 통과할 수 있습니다.
