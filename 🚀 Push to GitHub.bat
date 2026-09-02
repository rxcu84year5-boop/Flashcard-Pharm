@echo off
cd /d "%~dp0"

echo.
echo ============================================
echo   PharmaCU Flashcard Private - Push to GitHub
echo ============================================
echo.

git status --porcelain > tmp_status.txt 2>nul
set size=0
for %%A in (tmp_status.txt) do set size=%%~zA
del tmp_status.txt 2>nul

if "%size%"=="0" (
    echo [OK] No changes detected. Already up to date!
    echo.
    pause
    exit /b 0
)

echo [INFO] Changed files:
echo.
git status --short
echo.

set MYDATE=%date:~0,10%
set MYTIME=%time:~0,5%
set COMMIT_MSG=update: sync flashcards %MYDATE% %MYTIME%

echo [INFO] Commit: %COMMIT_MSG%
echo.

git add -A
git commit -m "%COMMIT_MSG%"
echo.

echo [INFO] Pushing to GitHub...
git push origin main

echo.
if %ERRORLEVEL%==0 (
    echo [SUCCESS] Push complete! Flashcards are now live on GitHub Pages.
) else (
    echo [ERROR] Push failed. Check your git remote or internet connection.
)
echo.
pause
