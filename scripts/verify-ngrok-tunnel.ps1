#Requires -Version 5.0
<#
.SYNOPSIS
  Tests whether an ngrok HTTPS URL reaches this Django app's /ping/ endpoint.

.DESCRIPTION
  Sends curl with ngrok-skip-browser-warning so the free-tier interstitial is bypassed.
  If you see "ok", the tunnel reaches Django; any browser-only blank page is not a broken tunnel.

.EXAMPLE
  .\scripts\verify-ngrok-tunnel.ps1 -Url "https://abc123.ngrok-free.dev"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Url
)

$Url = $Url.TrimEnd('/')
$pingUrl = "$Url/ping/"

Write-Host "Testing: $pingUrl" -ForegroundColor Cyan

try {
    $out = & curl.exe -sS -H "ngrok-skip-browser-warning: 1" --max-time 30 $pingUrl 2>&1
    $code = $LASTEXITCODE
} catch {
    Write-Host "curl failed: $_" -ForegroundColor Red
    exit 1
}

if ($code -ne 0) {
    Write-Host "curl exit code: $code" -ForegroundColor Red
    Write-Host $out
    exit $code
}

$body = ($out | Out-String).Trim()
if ($body -eq "ok") {
    Write-Host "SUCCESS: tunnel reaches Django (/ping/ returned ok)." -ForegroundColor Green
    Write-Host "If the browser still looks blank, see docs/NGROK_FREE_TIER_INTERSTITIAL.md" -ForegroundColor Yellow
    exit 0
}

if ($body -match 'ERR_NGROK_8012|failed to establish a connection to the upstream|Bad Gateway') {
    Write-Host "NGROK ERR_NGROK_8012: The ngrok agent is running, but nothing accepted the connection at the upstream address." -ForegroundColor Red
    Write-Host ""
    Write-Host "Do this:" -ForegroundColor Yellow
    Write-Host "  1. Start Django FIRST, on port 8000, e.g.:" -ForegroundColor White
    Write-Host "       python manage.py runserver 127.0.0.1:8000" -ForegroundColor Gray
    Write-Host "     or double-click runserver_global.bat" -ForegroundColor Gray
    Write-Host "  2. Start ngrok pointing at IPv4 (fixes Windows localhost -> [::1] issues):" -ForegroundColor White
    Write-Host "       ngrok http 127.0.0.1:8000" -ForegroundColor Gray
    Write-Host "     NOT only 'ngrok http 8000' if localhost resolves to IPv6 and Django listens on IPv4." -ForegroundColor DarkGray
    Write-Host "  3. Confirm in browser: http://127.0.0.1:8000/ping/ shows ok" -ForegroundColor White
    Write-Host ""
    Write-Host "See docs/NGROK_TUNNEL_CHECKLIST.md section ERR_NGROK_8012." -ForegroundColor DarkGray
    exit 3
}

Write-Host "Unexpected response (expected exactly 'ok'):" -ForegroundColor Yellow
Write-Host $body
exit 2
