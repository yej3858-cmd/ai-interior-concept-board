@echo off
cd /d "%~dp0"
echo Pulling latest updates...
git pull
echo Starting AI Interior Concept Board...
start python app.py
timeout /t 6 /nobreak >nul
start http://localhost:7861
