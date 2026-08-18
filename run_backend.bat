@echo off
title StockWatch Backend Server
cd /d "%~dp0\backend"
echo Starting StockWatch Flask Server...
venv\Scripts\python.exe app.py
pause
