@echo off
REM Double-click this after a power cut or restart. It opens 4 collector windows;
REM each continues from its own last saved page. Keep the windows open.
cd /d "%~dp0"
REM Use a specific Chromium build if present; otherwise Playwright's own (npm run setup).
if exist "%LOCALAPPDATA%\ms-playwright\chromium-1228\chrome-win64\chrome.exe" set CHROME_PATH=%LOCALAPPDATA%\ms-playwright\chromium-1228\chrome-win64\chrome.exe

REM Page ranges overlap by 150 pages so contracts that shift between pages are not missed.
start "Prohori collector 1" cmd /k node collect_noa.js --from 1     --to 22507 --delay-ms 1200
start "Prohori collector 2" cmd /k node collect_noa.js --from 22358 --to 44864 --delay-ms 1200 --worker w2
start "Prohori collector 3" cmd /k node collect_noa.js --from 44715 --to 67221 --delay-ms 1200 --worker w3
start "Prohori collector 4" cmd /k node collect_noa.js --from 67072 --to 90000 --delay-ms 1200 --worker w4

echo Started 4 collectors. You can close this window.
