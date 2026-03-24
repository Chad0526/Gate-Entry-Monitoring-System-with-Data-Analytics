@echo off
REM Bind Django dev server to all interfaces so phones, LAN, and ngrok can reach this PC.
REM For ngrok on Windows, use: ngrok-http-8000.bat (127.0.0.1:8000) to avoid ERR_NGROK_8012.
REM Windows Firewall may prompt to allow Python on private networks the first time.
cd /d "%~dp0"
python manage.py runserver 0.0.0.0:8000
