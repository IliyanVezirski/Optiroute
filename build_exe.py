"""
Скрипт за компилиране на CVRP програмата в EXE файл
Използва PyInstaller за създаване на standalone EXE
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """Проверява дали са инсталирани необходимите пакети"""
    required_packages = ['pyinstaller', 'ortools', 'pandas', 'openpyxl']
    
    print("🔍 Проверявам зависимости...")
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"❌ {package} - НЕ Е ИНСТАЛИРАН")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Липсват пакети: {', '.join(missing_packages)}")
        return False
    
    return True

def install_dependencies():
    """Инсталира липсващите зависимости"""
    print("\n📦 Инсталирам липсващи зависимости...")
    
    packages = ['pyinstaller', 'ortools', 'pandas', 'openpyxl']
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} - инсталиран")
        except subprocess.CalledProcessError:
            print(f"❌ Грешка при инсталиране на {package}")
            return False
    
    return True

def create_spec_file():
    """Създава .spec файл за PyInstaller"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_exe.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.py', '.'),
        ('input_handler.py', '.'),
        ('warehouse_manager.py', '.'),
        ('cvrp_solver.py', '.'),
        ('output_handler.py', '.'),
        ('osrm_client.py', '.'),
        ('data', 'data'),
    ],
    hiddenimports=[
        'ortools',
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

def build_exe():
    """Компилира EXE файла"""
    print("\n🔨 Стартирам компилиране на EXE...")
    
    try:
        # Използваме .spec файла за по-добър контрол
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
            return True
        else:
            print("❌ EXE файлът не е създаден!")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Грешка при компилиране: {e}")
        return False

def create_batch_file():
    """Създава .bat файл за лесно стартиране"""
    batch_content = '''@echo off
echo CVRP Optimizer - Стартиране...
echo.

REM Проверяваме дали има входен файл
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

def main():
    """Главна функция"""
    print("🚀 CVRP Optimizer - EXE Builder")
    print("=" * 40)
    
    # 1. Проверяваме зависимостите
    if not check_dependencies():
        print("\n❌ Липсват зависимости!")
        if input("Искате ли да инсталирам липсващите пакети? (y/n): ").lower() == 'y':
            if not install_dependencies():
                print("❌ Не успях да инсталирам зависимостите!")
                return
        else:
            print("❌ Не можете да продължите без необходимите пакети!")
            return
    
    # 2. Създаваме .spec файла
    create_spec_file()
    
    # 3. Компилираме EXE
    if build_exe():
        # 4. Създаваме .bat файл
        create_batch_file()
        
        print("\n🎉 Създаването на EXE файла завърши успешно!")
        print("\n📋 Следващи стъпки:")
        print("1. Копирайте dist/CVRP_Optimizer.exe в желаната директория")
        print("2. Създайте data/input.xlsx файл с вашите данни")
        print("3. Стартирайте CVRP_Optimizer.exe или start_cvrp.bat")
        
    else:
        print("\n❌ Създаването на EXE файла се провали!")

if __name__ == "__main__":
    main() 