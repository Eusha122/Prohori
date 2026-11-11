@echo off
REM Stops all collectors safely. Nothing is lost: each resumes from its bookmark next time.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object { $_.CommandLine -match 'collect_noa' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo All collectors stopped. Start again with START_COLLECTING_BACKGROUND.bat
pause
