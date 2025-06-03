@echo This will zip the source code and deploy it to the Azure Web App
pause
@echo off
rem change to folder where BAT file is
cd /d "%~dp0"
set SCRIPT=%~dp0DeployAzureWebApp.ps1
rem unblock the PowerShell script first
powershell.exe -Command "Unblock-File -Path %SCRIPT%"
rem now run the script
powershell.exe -f %SCRIPT%
pause