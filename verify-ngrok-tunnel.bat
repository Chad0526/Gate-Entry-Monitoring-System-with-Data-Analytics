@echo off
REM Test your ngrok URL against Django /ping/ (run from project folder).
REM Usage: verify-ngrok-tunnel.bat https://YOUR-SUBDOMAIN.ngrok-free.dev
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: %~nx0 https://your-subdomain.ngrok-free.dev
  echo Example: %~nx0 https://abc123.ngrok-free.dev
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\verify-ngrok-tunnel.ps1" -Url "%~1"
