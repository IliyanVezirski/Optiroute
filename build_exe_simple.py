"""
Опростен скрипт за компилиране на CVRP програмата в EXE файл
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Главна функция"""
    print("🚀 CVRP Optimizer - Опростен EXE Builder")
    print("=" * 40)
    
    # Проверяваме дали PyInstaller е наличен
    try:
        import PyInstaller
        print("✅ PyInstaller е наличен")
    except ImportError:
        print("❌ PyInstaller не е инсталиран!")
        print("Инсталирайте го с: pip install pyinstaller")
        return
    
    # Създаваме .spec файл
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_exe.py'],
    pathex=[],
    binaries=[
        ('.venv/Lib/site-packages/ortools/constraint_solver/_pywrapcp.pyd', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/linear_solver/_pywraplp.pyd', 'ortools/linear_solver'),
    ],
    datas=[
        ('config.py', '.'),
        ('input_handler.py', '.'),
        ('warehouse_manager.py', '.'),
        ('cvrp_solver.py', '.'),
        ('output_handler.py', '.'),
        ('osrm_client.py', '.'),
    ],
    hiddenimports=[
        'ortools',
        'ortools.constraint_solver',
        'ortools.constraint_solver.pywrapcp',
        'ortools.linear_solver',
        'ortools.linear_solver.pywraplp',
        'pandas',
        'openpyxl',
        'requests',
        'numpy',
        'multiprocessing',
        'logging',
        'pathlib',
        'typing',
        'dataclasses',
        'copy',
        'time',
        'os',
        'sys'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CVRP_Optimizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)
'''
    
    with open('CVRP_Optimizer.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ Създаден CVRP_Optimizer.spec файл")
    
    # Компилираме EXE
    print("\n🔨 Стартирам компилиране на EXE...")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            'CVRP_Optimizer.spec'
        ])
        
        print("✅ EXE файлът е създаден успешно!")
        
        # Проверяваме дали файлът съществува
        exe_path = Path('dist/CVRP_Optimizer.exe')
        if exe_path.exists():
            print(f"📁 EXE файл: {exe_path.absolute()}")
            
            # Създаваме batch файл
            batch_content = '''@echo off
echo CVRP Optimizer - Стартиране...
echo.

if exist "data\\input.xlsx" (
    echo Намерен входен файл: data\\input.xlsx
    CVRP_Optimizer.exe data\\input.xlsx
) else (
    echo Входен файл не е намерен. Стартирам с подразбиране...
    CVRP_Optimizer.exe
)

echo.
echo Натиснете Enter за да затворите...
pause
'''
            
            with open('start_cvrp.bat', 'w', encoding='utf-8') as f:
                f.write(batch_content)
            
            print("✅ Създаден start_cvrp.bat файл")
            print("\n🎉 Създаването на EXE файла завърши успешно!")
            
        else:
            print("❌ EXE файлът не е създаден!")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Грешка при компилиране: {e}")

if __name__ == "__main__":
    main() 