@echo off
title PharmaCU Flashcard Private -- Compile Offline Database
cls

echo ======================================================
echo   PharmaCU Flashcard Private -- Compile Database
echo   Fetching latest cards from Google Sheets (Private)
echo ======================================================
echo.
echo Compiling data... Please wait a few seconds.
echo.

cd /d "%~dp0"

python "compile_offline_db.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==========================================
    echo  ERROR: Compile failed!
    echo  Please check your Python or internet.
    echo ==========================================
    pause
    exit /b 1
)

echo.
echo ======================================================
echo  SUCCESS! Offline database compiled and updated.
echo  Ready to double-click 'Push to GitHub.bat'
echo ======================================================
echo.
pause
