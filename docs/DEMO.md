# 재현 가능한 데모

## 준비

```powershell
.\scripts\seed-demo.ps1
```

이 명령은 2025-01-01 09:00 UTC에 발생한 결제 capture 실패 3건을 만듭니다. 주문 ID, IP, UUID가 다르지만 하나의 fingerprint로 묶이고 세 번째 로그는 `critical`입니다. 기본 임계치 3건을 충족해 급증 event도 생성됩니다.

같은 명령을 다시 실행하면 `external_id`가 같아 3건 모두 중복으로 처리됩니다. 다른 재현 세트가 필요하면 backend에서 `python -m app.sample_data --seed 10`처럼 seed를 바꿉니다.

## 화면 확인 순서

1. 목록에서 `payments` 장애와 `치명적` badge를 확인합니다.
2. 상세에서 severity 근거, 원인 후보와 정확한 log ID를 확인합니다.
3. 대응 체크리스트와 상태 타임라인을 확인합니다.
4. `확인 시작`, `해결 처리`를 차례로 눌러 상태 이력을 만듭니다.
5. 같은 패턴의 새 error 로그를 넣어 해결된 incident가 다시 열리는지 확인합니다.
6. 별도 창에서 새 로그를 넣어 SSE 연결 상태와 목록 갱신을 확인합니다.

## 대표 화면 다시 만들기

```powershell
New-Item -ItemType Directory -Force docs\images | Out-Null
$env:CAPTURE_DEMO='true'
cd frontend
npx playwright test --config playwright.config.ts
```

실제 Edge E2E가 `docs/images/dashboard.png`를 만듭니다. 테스트용 DB와 서버는 실행마다 격리되고 종료 시 정리됩니다.
