@echo off
REM Double-click this after a power cut or restart. It opens 7 collector windows;
REM each continues from its own last saved page. Keep the windows open.
cd /d "%~dp0"
REM Use a specific Chromium build if present; otherwise Playwright's own (npm run setup).
if exist "%LOCALAPPDATA%\ms-playwright\chromium-1228\chrome-win64\chrome.exe" set CHROME_PATH=%LOCALAPPDATA%\ms-playwright\chromium-1228\chrome-win64\chrome.exe

REM Page ranges overlap by 150 pages so contracts that shift between pages are not missed.
REM w5-w7 were split off w2-w4 to finish faster; bookmarks (pages_done_*.txt) keep everything resumable.
start "Prohori collector 1" cmd /k node collect_noa.js --from 1     --to 22507 --delay-ms 1200
start "Prohori collector 2" cmd /k node collect_noa.js --from 22358 --to 40650 --delay-ms 1200 --worker w2
start "Prohori collector 7" cmd /k node collect_noa.js --from 40500 --to 44864 --delay-ms 1200 --worker w7
start "Prohori collector 3" cmd /k node collect_noa.js --from 44715 --to 62250 --delay-ms 1200 --worker w3
start "Prohori collector 5" cmd /k node collect_noa.js --from 62100 --to 67221 --delay-ms 1200 --worker w5
start "Prohori collector 4" cmd /k node collect_noa.js --from 67072 --to 83950 --delay-ms 1200 --worker w4
start "Prohori collector 6" cmd /k node collect_noa.js --from 83800 --to 90000 --delay-ms 1200 --worker w6

echo Started 7 collectors. You can close this window.
