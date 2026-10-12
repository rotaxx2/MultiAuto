$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if ($null -eq (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker не найден в PATH."
}

Write-Host "Stopping MultiAuto services..." -ForegroundColor Cyan
docker compose down
foreach ($containerName in @("multiauto_tunnel_backend", "multiauto_tunnel_frontend")) {
    $existing = docker ps -a --filter "name=^/$containerName$" --format "{{.Names}}"
    if ($existing -eq $containerName) {
        docker rm -f $containerName | Out-Null
    }
}
Write-Host "MultiAuto stopped. PostgreSQL/Redis volumes are kept." -ForegroundColor Green
