@echo off
title StockWatch Frontend Server
cd /d "%~dp0\Frontend"
echo Starting StockWatch Frontend Server on http://localhost:8000 ...
echo Please keep this window open and go to http://localhost:8000 in your browser!
echo.
python -m http.server 8000
pause
