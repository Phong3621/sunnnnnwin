@echo off
echo === SUNLON KEY SYSTEM - PUSH TO GITHUB ===
echo.

echo 1. Khoi tao Git repository...
git init

echo.
echo 2. Them tat ca files...
git add .

echo.
echo 3. Commit files...
git commit -m "Initial commit: SunLon Key Management System"

echo.
echo 4. Tao branch main...
git branch -M main

echo.
echo 5. Lien ket voi GitHub repository...
echo Vui long thay YOUR_USERNAME bang username GitHub cua ban
set /p username="Nhap username GitHub: "
git remote add origin https://github.com/%username%/sunlon-key-system.git

echo.
echo 6. Push len GitHub...
git push -u origin main

echo.
echo === HOAN THANH ===
echo Repository da duoc push len: https://github.com/%username%/sunlon-key-system
pause