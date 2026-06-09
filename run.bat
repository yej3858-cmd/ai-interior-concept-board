@echo off
cd /d "%~dp0"
echo Starting AI Interior Concept Board...
start python app.py
timeout /t 4 /nobreak >nul
start http://localhost:7860
