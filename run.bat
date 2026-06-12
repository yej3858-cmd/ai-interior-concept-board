@echo off
cd /d "%~dp0"
echo Pulling latest updates...
git pull

echo Closing any previous instance on port 7860...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :7860 ^| findstr LISTENING') do taskkill /F /PID %%P >nul 2>nul

echo Starting AI Interior Concept Board...
start python app.py
timeout /t 6 /nobreak >nul
start http://localhost:7860
