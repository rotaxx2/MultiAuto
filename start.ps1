$ErrorActionPreference = "Stop"

function Remove-ContainerIfExists {
    param([Parameter(Mandatory = $true)][string]$Name)
    $existing = docker ps -a --filter "name=^/$Name$" --format "{{.Names}}"
    if ($existing -eq $Name) {
        docker rm -f $Name | Out-Null
    }
}

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Read-DotEnv {
    param([Parameter(Mandatory = $true)][string]$Path)
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        $values[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim([char]39)
    }
    return $values
}

function Wait-HttpOk {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$Attempts = 60,
        [int]$DelaySeconds = 2
    )

    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds $DelaySeconds
        }
    }
    return $false
}

function Start-CloudflaredTunnel {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$TargetUrl
    )

    Remove-ContainerIfExists $Name
    Write-Host "Starting HTTPS tunnel '$Name' -> $TargetUrl ..." -ForegroundColor Cyan
    docker run -d --name $Name cloudflare/cloudflared:latest tunnel --no-autoupdate --url $TargetUrl | Out-Null

    for ($i = 1; $i -le 60; $i++) {
        $logs = & cmd /c "docker logs $Name 2>&1"
        $match = [regex]::Match(($logs -join "`n"), "https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        if ($match.Success) {
            return $match.Value
        }
        Start-Sleep -Seconds 1
    }

    docker logs $Name
    Write-Error "Could not get public HTTPS URL for tunnel '$Name'."
}

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Test-Command "docker")) {
    Write-Error "Docker was not found in PATH. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
}

if (-not (Test-Path -LiteralPath ".env")) {
    Write-Error ".env file was not found. Create it once: Copy-Item .env.example .env, then fill TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_USERNAME."
}

$envValues = Read-DotEnv ".env"
$required = @("SECRET_KEY", "POSTGRES_PASSWORD", "TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_USERNAME")
$missing = @()
foreach ($key in $required) {
    if (-not $envValues.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($envValues[$key]) -or $envValues[$key] -eq "change-me") {
        $missing += $key
    }
}

if ($missing.Count -gt 0) {
    Write-Error ("Missing required variables in .env: " + ($missing -join ", "))
}

$orgSlug = $envValues["TELEGRAM_DEFAULT_ORGANIZATION_SLUG"]
if ([string]::IsNullOrWhiteSpace($orgSlug)) {
    $orgSlug = "clean-auto"
    Write-Warning "TELEGRAM_DEFAULT_ORGANIZATION_SLUG is empty. Demo data will use slug '$orgSlug'. Use /start org_$orgSlug or set slug in .env."
}

$botUsername = $envValues["TELEGRAM_BOT_USERNAME"]

$backendPort = $envValues["BACKEND_PORT"]
if ([string]::IsNullOrWhiteSpace($backendPort)) {
    $backendPort = "8000"
}

$frontendPort = $envValues["FRONTEND_PORT"]
if ([string]::IsNullOrWhiteSpace($frontendPort)) {
    $frontendPort = "5173"
}

Write-Host "Starting database, Redis, backend and background workers..." -ForegroundColor Cyan
docker compose up --build -d postgres redis backend celery_worker celery_beat

Write-Host "Waiting for backend health check..." -ForegroundColor Cyan
$backendUrl = "http://localhost:$backendPort/health/"

if (-not (Wait-HttpOk $backendUrl)) {
    docker compose ps
    Write-Error "Backend did not become available at $backendUrl. Check logs: docker compose logs -f backend"
}

Write-Host "Preparing local demo organization '$orgSlug'..." -ForegroundColor Cyan
docker compose exec -T backend python manage.py seed_demo_data --slug $orgSlug

$publicBackendUrl = Start-CloudflaredTunnel "multiauto_tunnel_backend" "http://host.docker.internal:$backendPort"

Write-Host "Starting frontend with public backend API URL: $publicBackendUrl" -ForegroundColor Cyan
$env:VITE_API_URL = $publicBackendUrl
docker compose up --build -d frontend

$localFrontendUrl = "http://localhost:$frontendPort"
if (-not (Wait-HttpOk $localFrontendUrl 60 2)) {
    docker compose ps
    Write-Error "Frontend did not become available at $localFrontendUrl. Check logs: docker compose logs -f frontend"
}

$publicFrontendUrl = Start-CloudflaredTunnel "multiauto_tunnel_frontend" "http://host.docker.internal:$frontendPort"

Write-Host "Restarting backend with phone Mini App CORS settings..." -ForegroundColor Cyan
$env:ALLOWED_HOSTS = "localhost,127.0.0.1,backend,.trycloudflare.com"
$env:CORS_ALLOWED_ORIGINS = "http://localhost:$frontendPort,http://127.0.0.1:$frontendPort,$publicFrontendUrl"
$env:CSRF_TRUSTED_ORIGINS = "http://localhost:$frontendPort,http://127.0.0.1:$frontendPort,$publicFrontendUrl"
docker compose up -d --force-recreate backend

if (-not (Wait-HttpOk $backendUrl)) {
    docker compose ps
    Write-Error "Backend did not restart after CORS setup. Check logs: docker compose logs -f backend"
}

Write-Host "Starting Telegram bot with Mini App URL: $publicFrontendUrl" -ForegroundColor Cyan
$env:TELEGRAM_MINI_APP_URL = $publicFrontendUrl
docker compose up -d --force-recreate telegram_bot

Write-Host ""
Write-Host "MultiAuto started." -ForegroundColor Green
Write-Host "Local backend:    $backendUrl"
Write-Host "Phone backend:    $publicBackendUrl"
Write-Host "Local frontend:   $localFrontendUrl"
Write-Host "Phone Mini App:   $publicFrontendUrl"
Write-Host ""
Write-Host "Send /start org_$orgSlug to @$botUsername"
Write-Host ""
Write-Host "Useful commands:"
Write-Host "  docker compose ps"
Write-Host "  docker compose logs -f telegram_bot"
Write-Host "  docker compose logs -f frontend"
Write-Host "  .\stop.ps1"
