@echo off
rem change to folder where BAT file is
cd /d "%~dp0"
set SCRIPT=%~dp0TestEndPoint.ps1
rem unblock the PowerShell script first
powershell.exe -Command "Unblock-File -Path %SCRIPT%"
rem now run the script
powershell.exe -f %SCRIPT%
pause