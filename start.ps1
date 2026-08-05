# Sovg'a Bot — ishga tushirish
# Cloudflare tunnel ochadi, manzilni .env ga yozadi, menyu tugmasini yangilaydi va botni ishga tushiradi.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $root ".env"
$cf = "C:\Program Files (x86)\cloudflared\cloudflared.exe"

if (-not (Test-Path $envFile)) { Write-Host "XATO: .env fayli topilmadi" -F Red; exit 1 }
if (-not (Test-Path $cf))      { Write-Host "XATO: cloudflared topilmadi" -F Red; exit 1 }

$token = ((Get-Content $envFile | Select-String '^BOT_TOKEN=') -split '=', 2)[1].Trim()
if (-not $token) { Write-Host "XATO: .env da BOT_TOKEN yo'q" -F Red; exit 1 }

# --- 1. Tunnel ---
Write-Host "`n[1/4] Tunnel ochilmoqda..." -F Cyan
$log = Join-Path $env:TEMP "quizbot-cf.log"
if (Test-Path $log) { Clear-Content $log }
$proc = Start-Process $cf -ArgumentList "tunnel", "--url", "http://localhost:8080" `
        -RedirectStandardError $log -RedirectStandardOutput "$log.out" -WindowStyle Hidden -PassThru

$url = $null
foreach ($i in 1..30) {
    Start-Sleep -Milliseconds 1000
    if (Test-Path $log) {
        $m = Select-String -Path $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value; break }
    }
}
if (-not $url) {
    Write-Host "XATO: tunnel manzili olinmadi. Log: $log" -F Red
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "      $url" -F Green

# --- 2. .env ---
Write-Host "[2/4] .env yangilanmoqda..." -F Cyan
(Get-Content $envFile) -replace '^WEBAPP_URL=.*', "WEBAPP_URL=$url" | Set-Content -Encoding utf8 $envFile

# --- 3. Menyu tugmasi ---
Write-Host "[3/4] Telegram menyu tugmasi yangilanmoqda..." -F Cyan
$body = @{ menu_button = @{ type = "web_app"; text = "🎁 Ilova"; web_app = @{ url = $url } } } | ConvertTo-Json -Depth 5
try {
    Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$token/setChatMenuButton" `
        -ContentType "application/json; charset=utf-8" `
        -Body ([Text.Encoding]::UTF8.GetBytes($body)) | Out-Null
    Write-Host "      OK" -F Green
} catch { Write-Host "      Ogohlantirish: menyu tugmasi yangilanmadi" -F Yellow }

# --- 4. Bot ---
Write-Host "[4/4] Bot va WebApp ishga tushmoqda...`n" -F Cyan
Write-Host "To'xtatish uchun: Ctrl+C`n" -F DarkGray
try {
    python (Join-Path $root "app.py")
} finally {
    Write-Host "`nTunnel yopilmoqda..." -F DarkGray
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}
