@echo off
set ROM_PATH=%~1
set ROM_NAME=%~n1

REM 1. Change to RetroArch directory and run the game
cd /d "C:\Retroarch"
"C:\Retroarch\retroarch.exe" -L cores\fbneo_libretro.dll "%ROM_PATH%"

REM 2. Once RetroArch is closed, go to ScoreBridge and upload the record
cd /d "C:\AttractModePlus\ScoreBridge"
python scorebridge.py %ROM_NAME%
