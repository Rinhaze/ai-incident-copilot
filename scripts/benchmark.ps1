param([ValidateRange(1, 1000)][int]$Count = 1000)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$python = Join-Path $project 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'backend 가상환경이 없습니다. README의 설치 절차를 먼저 실행해 주세요.'
}
Push-Location (Join-Path $project 'backend')
try {
    & $python scripts\benchmark.py --count $Count --output "..\benchmark-results\latest.json"
    if ($LASTEXITCODE -ne 0) { throw '개발 환경 회귀 측정에 실패했습니다.' }
} finally { Pop-Location }
