@echo off
REM Double-click to see how far the e-GP data collection has got.
cd /d "%~dp0..\data\raw\noa"
for /f %%n in ('type pages_done*.txt 2^>nul ^| find /c /v ""') do set DONE=%%n
for /f %%n in ('tasklist /fi "imagename eq node.exe" ^| find /c "node.exe"') do set RUNNING=%%n
set /a PCT=DONE*100/89900
echo.
echo   Prohori data collection
echo   -----------------------
echo   Pages collected : %DONE% of about 89900  (%PCT%%%)
echo   Collectors running : %RUNNING%  (7 = all running, 0 = stopped or finished)
echo.
pause
