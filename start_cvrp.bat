@echo off
echo CVRP Optimizer - Стартиране...
echo.

if exist "data\input.xlsx" (
    echo Намерен входен файл: data\input.xlsx
    CVRP_Optimizer.exe data\input.xlsx
) else (
    echo Входен файл не е намерен. Стартирам с подразбиране...
    CVRP_Optimizer.exe
)

echo.
echo Натиснете Enter за да затворите...
pause
