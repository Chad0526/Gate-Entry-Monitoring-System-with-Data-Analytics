@echo off
title ngrok - CCB Gate Entry
echo Starting ngrok (exposing localhost:8000)...
echo.
ngrok http 8000
pause
