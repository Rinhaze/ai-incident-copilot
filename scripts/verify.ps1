param([switch]$SkipE2E, [switch]$SkipAudits)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$python = Join-Path $project 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'backend 가상환경이 없습니다. README의 설치 절차를 먼저 실행해 주세요.'
}

Write-Host '1/4 백엔드 테스트'
Push-Location (Join-Path $project 'backend')
try {
    # 서로 다른 Windows 실행 주체가 이전 pytest 임시 폴더를 소유해도 충돌하지 않도록
    # 검증 실행마다 고유한 경로를 사용한다.
    $testRunDirectory = '.verify-' + [guid]::NewGuid().ToString('N')
    & $python -m pytest -q --basetemp $testRunDirectory
    if ($LASTEXITCODE -ne 0) { throw '백엔드 테스트에 실패했습니다.' }
    if (-not $SkipAudits) {
        & $python -m pip_audit -r requirements.txt --progress-spinner off
        if ($LASTEXITCODE -ne 0) { throw 'Python 의존성 감사에 실패했습니다.' }
    }
} finally { Pop-Location }

Write-Host '2/4 프런트엔드 테스트'
Push-Location (Join-Path $project 'frontend')
try {
    & npm test -- --run
    if ($LASTEXITCODE -ne 0) { throw '프런트엔드 테스트에 실패했습니다.' }
    Write-Host '3/4 프런트엔드 빌드와 의존성 감사'
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw '프런트엔드 production build에 실패했습니다.' }
    if (-not $SkipAudits) {
        & npm audit --audit-level=high
        if ($LASTEXITCODE -ne 0) { throw 'npm 의존성 감사에 실패했습니다.' }
    }
    if (-not $SkipE2E) {
        Write-Host '4/4 설치된 Microsoft Edge 기반 E2E'
        & npx playwright test --config playwright.config.ts
        if ($LASTEXITCODE -ne 0) { throw 'Microsoft Edge E2E에 실패했습니다.' }
    } else { Write-Host '4/4 E2E 생략' }
} finally { Pop-Location }

Write-Host '전체 로컬 검증을 통과했습니다.'
