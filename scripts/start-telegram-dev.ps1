param(
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [string]$FrontendHost = "127.0.0.1",
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $Root ".env"
$BackendPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
$FrontendDir = Join-Path $Root "frontend"
$DevDir = Join-Path $Root ".dev-logs"
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$LogDir = Join-Path $DevDir $RunId
$PidFile = Join-Path $DevDir "telegram-dev-pids.txt"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$backend = $null
$frontend = $null
$tunnel = $null
$bot = $null
$reminderWorker = $null

trap {
    Stop-DevProcess $bot
    Stop-DevProcess $reminderWorker
    Stop-DevProcess $tunnel
    Stop-DevProcess $frontend
    Stop-DevProcess $backend
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    throw
}

function Set-EnvValue {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value
    )

    $line = "$Name=$Value"
    if (Test-Path $Path) {
        $content = Get-Content $Path
        $updated = $false
        $next = foreach ($item in $content) {
            if ($item -match "^$([regex]::Escape($Name))=") {
                $updated = $true
                $line
            } else {
                $item
            }
        }
        if (-not $updated) {
            $next += $line
        }
        Set-Content -Path $Path -Value $next
    } else {
        Set-Content -Path $Path -Value $line
    }
}

function Stop-DevProcess {
    param([System.Diagnostics.Process]$Process)

    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
}

function Stop-PreviousDevProcesses {
    if (-not (Test-Path $PidFile)) {
        return
    }

    Write-Host "Stopping previous dev processes from $PidFile ..."
    foreach ($line in Get-Content $PidFile) {
        if ($line -match "^\d+$") {
            Stop-Process -Id ([int]$line) -Force -ErrorAction SilentlyContinue
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

function Save-DevPid {
    param([System.Diagnostics.Process]$Process)

    if ($null -ne $Process) {
        Add-Content -Path $PidFile -Value $Process.Id
    }
}

function Stop-ProjectDevProcesses {
    Write-Host "Stopping old MultiAuto dev processes if any ..."
    try {
        $escapedRoot = $Root.Replace("\", "\\")
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.CommandLine -and
                $_.ProcessId -ne $PID -and
                (
                    ($_.CommandLine -match [regex]::Escape($Root) -and $_.CommandLine -match "manage\.py" -and ($_.CommandLine -match "runserver" -or $_.CommandLine -match "run_telegram_bot" -or $_.CommandLine -match "run_booking_reminder_worker")) -or
                    ($_.CommandLine -match [regex]::Escape($FrontendDir) -and $_.CommandLine -match "vite")
                )
            } |
            ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
    } catch {
        Write-Host "Could not inspect old dev processes. Continuing with PID-file cleanup only."
    }
}

function Assert-ProcessRunning {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Name,
        [string]$ErrorLog
    )

    if ($null -eq $Process -or $Process.HasExited) {
        $details = ""
        if (Test-Path $ErrorLog) {
            $details = Get-Content $ErrorLog -Raw
        }
        throw "$Name exited during startup. Log: $ErrorLog`n$details"
    }
}

function Invoke-Django {
    param([string[]]$Arguments)

    & $BackendPython @Arguments "--settings=config.settings.test"
    if ($LASTEXITCODE -ne 0) {
        throw "Django command failed: $($Arguments -join ' ')"
    }
}

if (-not (Test-Path $BackendPython)) {
    throw "Python venv not found: $BackendPython"
}

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared is not available in PATH. Install Cloudflare Tunnel or add cloudflared.exe to PATH."
}

Stop-PreviousDevProcesses
Stop-ProjectDevProcesses
Set-Content -Path $PidFile -Value @()

$backendUrl = "http://${BackendHost}:${BackendPort}"
$frontendUrl = "http://${FrontendHost}:${FrontendPort}"
$cloudflaredOutLog = Join-Path $LogDir "cloudflared.out.log"
$cloudflaredErrLog = Join-Path $LogDir "cloudflared.err.log"

Write-Host "Preparing local SQLite database ..."
Invoke-Django -Arguments @("backend\manage.py", "migrate", "--noinput")
Invoke-Django -Arguments @("backend\manage.py", "seed_demo_data", "--slug", "clean-auto")

Write-Host "Starting Django backend at $backendUrl ..."
$backend = Start-Process -FilePath $BackendPython `
    -ArgumentList @("backend\manage.py", "runserver", "${BackendHost}:${BackendPort}", "--settings=config.settings.test") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput (Join-Path $LogDir "backend.out.log") `
    -RedirectStandardError (Join-Path $LogDir "backend.err.log") `
    -WindowStyle Hidden `
    -PassThru
Save-DevPid $backend

Start-Sleep -Seconds 3
Assert-ProcessRunning $backend "Django backend" (Join-Path $LogDir "backend.err.log")

Write-Host "Starting Vite frontend at $frontendUrl ..."
$frontend = Start-Process -FilePath "powershell" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ".\node_modules\.bin\vite.cmd --host $FrontendHost --port $FrontendPort") `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput (Join-Path $LogDir "frontend.out.log") `
    -RedirectStandardError (Join-Path $LogDir "frontend.err.log") `
    -WindowStyle Hidden `
    -PassThru
Save-DevPid $frontend

Start-Sleep -Seconds 3
Assert-ProcessRunning $frontend "Vite frontend" (Join-Path $LogDir "frontend.err.log")

Write-Host "Starting Cloudflare Tunnel to $frontendUrl ..."
$tunnel = Start-Process -FilePath "cloudflared" `
    -ArgumentList @("tunnel", "--url", $frontendUrl) `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $cloudflaredOutLog `
    -RedirectStandardError $cloudflaredErrLog `
    -WindowStyle Hidden `
    -PassThru
Save-DevPid $tunnel
Start-Sleep -Seconds 2
Assert-ProcessRunning $tunnel "Cloudflare Tunnel" $cloudflaredErrLog

$publicUrl = $null
for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 1
    $log = ""
    if (Test-Path $cloudflaredOutLog) {
        $log += Get-Content $cloudflaredOutLog -Raw
    }
    if (Test-Path $cloudflaredErrLog) {
        $log += Get-Content $cloudflaredErrLog -Raw
    }
    if ($log) {
        $match = [regex]::Match($log, "https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        if ($match.Success) {
            $publicUrl = $match.Value
            break
        }
    }
}

if (-not $publicUrl) {
    Stop-DevProcess $backend
    Stop-DevProcess $frontend
    Stop-DevProcess $tunnel
    throw "Could not detect Cloudflare Tunnel URL. See $cloudflaredOutLog and $cloudflaredErrLog"
}

Set-EnvValue -Path $EnvPath -Name "TELEGRAM_MINI_APP_URL" -Value $publicUrl
Set-EnvValue -Path $EnvPath -Name "CORS_ALLOWED_ORIGINS" -Value "http://localhost:5173,http://127.0.0.1:5173,$publicUrl"
Set-EnvValue -Path $EnvPath -Name "CSRF_TRUSTED_ORIGINS" -Value "http://localhost:5173,http://127.0.0.1:5173,$publicUrl"

Write-Host ""
Write-Host "Mini App public URL: $publicUrl" -ForegroundColor Green
Write-Host "Updated .env TELEGRAM_MINI_APP_URL."
Write-Host ""
Write-Host "Starting Telegram bot polling ..."
$bot = Start-Process -FilePath $BackendPython `
    -ArgumentList @("backend\manage.py", "run_telegram_bot", "--settings=config.settings.test") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput (Join-Path $LogDir "bot.out.log") `
    -RedirectStandardError (Join-Path $LogDir "bot.err.log") `
    -WindowStyle Hidden `
    -PassThru
Save-DevPid $bot
Start-Sleep -Seconds 3
Assert-ProcessRunning $bot "Telegram bot" (Join-Path $LogDir "bot.err.log")

Write-Host "Starting booking reminder worker ..."
$reminderWorker = Start-Process -FilePath $BackendPython `
    -ArgumentList @("backend\manage.py", "run_booking_reminder_worker", "--settings=config.settings.test") `
    -WorkingDirectory $Root `
    -RedirectStandardOutput (Join-Path $LogDir "reminders.out.log") `
    -RedirectStandardError (Join-Path $LogDir "reminders.err.log") `
    -WindowStyle Hidden `
    -PassThru
Save-DevPid $reminderWorker
Start-Sleep -Seconds 2
Assert-ProcessRunning $reminderWorker "Booking reminder worker" (Join-Path $LogDir "reminders.err.log")

Write-Host ""
Write-Host "Open Telegram on your phone, send /start to the bot, and tap the Mini App button."
Write-Host "Logs are in: $LogDir"
Write-Host "Press Enter here to stop backend, frontend, tunnel, bot, and reminders."
[void][System.Console]::ReadLine()

Stop-DevProcess $bot
Stop-DevProcess $reminderWorker
Stop-DevProcess $tunnel
Stop-DevProcess $frontend
Stop-DevProcess $backend
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue

Write-Host "Stopped dev services."
