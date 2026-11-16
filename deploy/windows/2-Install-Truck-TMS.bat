@echo off
rem Truck TMS installer - step 2. Double-click (NOT as administrator), after step 1 and a restart.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\2-install-truck-tms.ps1"
pause
