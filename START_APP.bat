@echo off
REM Double-click to start the Prohori prototype, then open http://localhost:8000 in Chrome.
cd /d "%~dp0"
echo Prohori is starting... open http://localhost:8000 in your browser.
echo Keep this window open while using the app.
start "" http://localhost:8000
.venv\Scripts\python -m uvicorn app.main:app --port 8000
pause
