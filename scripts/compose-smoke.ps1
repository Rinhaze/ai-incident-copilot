param([switch]$Postgres)
$ErrorActionPreference = 'Stop'
$files = @('-f', 'docker-compose.yml')
if ($Postgres) { $files += @('-f', 'docker-compose.postgres.yml', '--profile', 'postgres') }
try {
  & docker compose @files up --build -d
  if ($LASTEXITCODE -ne 0) { throw 'Docker Compose 빌드 또는 시작에 실패했습니다.' }
  $deadline = (Get-Date).AddMinutes(2)
  do {
    try { $health = Invoke-RestMethod 'http://127.0.0.1:5173/health'; if ($health.status -eq 'ok') { Write-Host 'Compose smoke 성공'; exit 0 } } catch {}
    Start-Sleep -Seconds 2
  } while ((Get-Date) -lt $deadline)
  throw '2분 안에 health endpoint가 준비되지 않았습니다.'
} finally {
  & docker compose @files down -v --remove-orphans
}
