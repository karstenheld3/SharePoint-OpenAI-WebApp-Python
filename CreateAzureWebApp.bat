@echo off
set PWSH="C:\Program Files\PowerShell\7\pwsh.exe"

if not exist %PWSH% (
    echo ERROR: PowerShell 7 not found at '%PWSH%'
    echo Please install PowerShell 7 from: https://github.com/PowerShell/PowerShell/releases
    pause
    exit /b 1
)

echo This will create the web app in Azure based on the configuration in the .env file
pause

rem change to folder where BAT file is
cd /d "%~dp0"
set SCRIPT=%~dp0CreateAzureWebApp.ps1

rem unblock the PowerShell script first
%PWSH% -Command "Unblock-File -Path %SCRIPT%"

rem now run the script with PowerShell 7
%PWSH% -f %SCRIPT%
pause