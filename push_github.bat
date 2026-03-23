@echo off
chcp 65001 >nul
cls
echo ====================================================
echo     PUSH DU AN LEN GITHUB
echo ====================================================
echo.

setlocal enabledelayedexpansion

git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git chua duoc cai dat!
    echo Chay: winget install --id Git.Git -e --source winget
    pause
    exit /b 1
)

echo [1/6] Kiem tra status...
git status
echo.

echo [2/6] Them tat ca files...
git add .
echo.

echo [3/6] Commit...
git commit -m "Add Telegram bot + webhook payment + auto-refresh key expiration"
echo.

echo [4/6] Tao branch main...
git branch -M main
echo.

echo [5/6] Nhap GitHub repository URL:
echo Vi du: https://github.com/your_username/sunlon-key-system.git
set /p REPO_URL="Repository URL: "

echo [6/6] Push len GitHub...
git remote add origin %REPO_URL% 2>nul
git push -u origin main

echo.
echo ====================================================
echo [SUCCESS] Da push thanh cong!
echo Repository: %REPO_URL%
echo ====================================================
pause
