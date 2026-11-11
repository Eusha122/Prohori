@echo off
REM Starts all 7 collectors hidden and at low priority (games keep priority).
REM Each continues from its own bookmark. Use CHECK_PROGRESS.bat to see progress.
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\ms-playwright\chromium-1228\chrome-win64\chrome.exe" set CHROME_PATH=%LOCALAPPDATA%\ms-playwright\chromium-1228\chrome-win64\chrome.exe
powershell -NoProfile -Command ^
  "$jobs = @('--from 1 --to 22507 --delay-ms 1200','--from 22358 --to 40650 --delay-ms 1200 --worker w2','--from 40500 --to 44864 --delay-ms 1200 --worker w7','--from 44715 --to 62250 --delay-ms 1200 --worker w3','--from 62100 --to 67221 --delay-ms 1200 --worker w5','--from 67072 --to 83950 --delay-ms 1200 --worker w4','--from 83800 --to 90000 --delay-ms 1200 --worker w6');" ^
  "foreach ($a in $jobs) { Start-Process cmd.exe -WindowStyle Hidden -WorkingDirectory '%~dp0' -ArgumentList '/c', ('start \"\" /belownormal /b /wait node collect_noa.js ' + $a) }"
echo Started 7 hidden collectors. Double-click CHECK_PROGRESS.bat to see progress.
timeout /t 5 >nul
