@echo off
echo ========================================
echo CVRP Optimizer - EXE Builder
echo ========================================
echo.

REM Проверяваме дали Python е инсталиран
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не е намерен! Моля инсталирайте Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python е намерен
echo.

REM Инсталираме необходимите пакети
echo 📦 Инсталирам зависимости...
pip install pyinstaller ortools pandas openpyxl requests numpy

if errorlevel 1 (
    echo ❌ Грешка при инсталиране на зависимостите!
    pause
    exit /b 1
)

echo ✅ Зависимостите са инсталирани
echo.

REM Създаваме .spec файл
echo 🔧 Създавам конфигурационен файл...
python build_exe.py

if errorlevel 1 (
    echo ❌ Грешка при създаване на конфигурацията!
    pause
    exit /b 1
)

echo.
echo 🎉 EXE файлът е готов!
echo 📁 Намира се в: dist\CVRP_Optimizer.exe
echo.
echo 💡 За да стартирате програмата:
echo    1. Копирайте CVRP_Optimizer.exe в желаната директория
echo    2. Създайте data\input.xlsx файл с вашите данни
echo    3. Стартирайте CVRP_Optimizer.exe
echo.
pause 