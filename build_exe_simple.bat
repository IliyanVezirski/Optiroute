@echo off
echo ========================================
echo Създаване на OptiRoute EXE файл
echo ========================================

echo.
echo 1. Изчистване на стари файлове...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo.
echo 2. Създаване на EXE файл...
pyinstaller --onefile --console --name OptiRoute main.py

echo.
echo 3. Проверка на резултата...
if exist "dist\OptiRoute.exe" (
    echo ✅ EXE файлът е създаден успешно!
    echo 📁 Намира се в: dist\OptiRoute.exe
    echo.
    echo За да стартирате програмата:
    echo   dist\OptiRoute.exe
) else (
    echo ❌ Грешка при създаване на EXE файл!
)

echo.
echo ========================================
pause 