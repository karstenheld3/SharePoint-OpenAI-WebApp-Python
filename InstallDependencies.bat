@echo This will install all dependencies listed in ./src/requirements.txt
pause
@echo off
rem change to folder where BAT file is
cd /d "%~dp0"
pip install -r ./src/requirements.txt
pause