@echo off
REM Start ngrok tunnel to Django on IPv4 (avoids ERR_NGROK_8012 when localhost -> [::1] on Windows).
REM Start Django FIRST: runserver_global.bat or: python manage.py runserver 127.0.0.1:8000
cd /d "%~dp0"
echo.
echo  Starting ngrok -^> http://127.0.0.1:8000
echo  If you see ERR_NGROK_8012, start Django on port 8000 first.
echo.
ngrok http 127.0.0.1:8000
