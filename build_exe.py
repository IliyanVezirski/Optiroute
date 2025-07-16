"""
Скрипт за компилиране на CVRP програмата в EXE файл
Използва PyInstaller за създаване на standalone EXE

Актуализиран за поддръжка на:
- Всички типове превозни средства (INTERNAL_BUS, CENTER_BUS, EXTERNAL_BUS, SPECIAL_BUS)
- Логика за център зона и глоби
- Повторно стартиране на програмата след завършване
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """Проверява дали са инсталирани необходимите пакети"""
    required_packages = ['pyinstaller', 'pandas', 'openpyxl', 'requests', 'numpy']
    optional_packages = ['ortools', 'tqdm', 'colorama']
    
    print("🔍 Проверявам зависимости...")
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"❌ {package} - НЕ Е ИНСТАЛИРАН")
            missing_packages.append(package)
    
    print("\n🔍 Проверявам опционални пакети...")
    for package in optional_packages:
        try:
            __import__(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"⚠️ {package} - НЕ Е ИНСТАЛИРАН (опционален)")
    
    if missing_packages:
        print(f"\n❌ Липсват задължителни пакети: {', '.join(missing_packages)}")
        return False
    
    return True

def install_dependencies():
    """Инсталира липсващите зависимости"""
    print("\n📦 Инсталирам липсващи зависимости...")
    
    required_packages = ['pyinstaller', 'pandas', 'openpyxl', 'requests', 'numpy']
    optional_packages = ['ortools', 'tqdm', 'colorama']
    
    print("📦 Инсталирам задължителни пакети...")
    for package in required_packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} - инсталиран")
        except subprocess.CalledProcessError:
            print(f"❌ Грешка при инсталиране на {package}")
            return False
    
    print("\n📦 Инсталирам опционални пакети...")
    for package in optional_packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} - инсталиран")
        except subprocess.CalledProcessError:
            print(f"⚠️ Грешка при инсталиране на {package} (опционален)")
    
    return True

def create_spec_file():
    """Създава .spec файл за PyInstaller"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_exe.py'],
    pathex=[],
    binaries=[
        # OR-Tools DLL файлове - всички необходими
        ('.venv/Lib/site-packages/ortools/.libs/ortools.dll', '.'),
        ('.venv/Lib/site-packages/ortools/.libs/abseil_dll.dll', '.'),
        ('.venv/Lib/site-packages/ortools/.libs/libprotobuf.dll', '.'),
        ('.venv/Lib/site-packages/ortools/.libs/re2.dll', '.'),
        ('.venv/Lib/site-packages/ortools/.libs/zlib1.dll', '.'),
        ('.venv/Lib/site-packages/ortools/.libs/libscip.dll', '.'),
        ('.venv/Lib/site-packages/ortools/.libs/libutf8_validity.dll', '.'),
        ('.venv/Lib/site-packages/ortools/.libs/highs.dll', '.'),
        ('.venv/Lib/site-packages/ortools/.libs/bz2.dll', '.'),
        # OR-Tools PYD файлове
        ('.venv/Lib/site-packages/ortools/constraint_solver/_pywrapcp.pyd', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/linear_solver/_pywraplp.pyd', 'ortools/linear_solver'),
    ],
    datas=[
        ('input_handler.py', '.'),
        ('warehouse_manager.py', '.'),
        ('cvrp_solver.py', '.'),
        ('output_handler.py', '.'),
        ('osrm_client.py', '.'),
        ('config.py', '.'),  # Добавено за да е сигурно, че конфигурацията с SPECIAL_BUS ще бъде включена
        ('main.py', '.'),    # Добавено за цялост
        ('main_exe.py', '.'), # Добавено за цялост
        ('data', 'data'),
        ('logs', 'logs'),    # Добавено за логове
        ('output', 'output'), # Добавено за изходни данни
        # OR-Tools protobuf файлове - всички необходими
        ('.venv/Lib/site-packages/ortools/constraint_solver/routing_parameters_pb2.py', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/routing_enums_pb2.py', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/assignment_pb2.py', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/search_stats_pb2.py', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/search_limit_pb2.py', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/solver_parameters_pb2.py', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/routing_ils_pb2.py', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/linear_solver/linear_solver_pb2.py', 'ortools/linear_solver'),
        # OR-Tools __init__.py файлове
        ('.venv/Lib/site-packages/ortools/__init__.py', 'ortools'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/__init__.py', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/linear_solver/__init__.py', 'ortools/linear_solver'),
        # OR-Tools допълнителни файлове
        ('.venv/Lib/site-packages/ortools/constraint_solver/routing_parameters_pb2.pyi', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/routing_enums_pb2.pyi', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/assignment_pb2.pyi', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/search_stats_pb2.pyi', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/search_limit_pb2.pyi', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/solver_parameters_pb2.pyi', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/constraint_solver/routing_ils_pb2.pyi', 'ortools/constraint_solver'),
        ('.venv/Lib/site-packages/ortools/linear_solver/linear_solver_pb2.pyi', 'ortools/linear_solver'),
    ],
    hiddenimports=[
        'ortools',
        'ortools.constraint_solver',
        'ortools.constraint_solver.pywrapcp',
        'ortools.linear_solver',
        'ortools.linear_solver.pywraplp',
        'ortools.constraint_solver.routing_parameters_pb2',
        'ortools.constraint_solver.routing_enums_pb2',
        'ortools.constraint_solver.assignment_pb2',
        'ortools.constraint_solver.search_stats_pb2',
        'ortools.constraint_solver.search_limit_pb2',
        'ortools.constraint_solver.solver_parameters_pb2',
        'ortools.constraint_solver.routing_ils_pb2',
        'ortools.linear_solver.linear_solver_pb2',
        'pandas',
        'pandas._libs',
        'pandas.core',
        'pandas.core.frame',
        'pandas.core.series',
        'pandas.io',
        'pandas.io.excel',
        'pandas.io.excel._openpyxl',
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.workbook',
        'openpyxl.worksheet',
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
        'sys',
        'tqdm',
        'colorama',
        'enum'  # Добавено за поддръжка на VehicleType.SPECIAL_BUS
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'PIL',
        'tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6'
    ],
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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='data/icon.ico' if os.path.exists('data/icon.ico') else None,
    version='file_version_info.txt' if os.path.exists('file_version_info.txt') else None
)
'''
    
    with open('CVRP_Optimizer.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ Създаден CVRP_Optimizer.spec файл")

def create_version_info():
    """Създава файл с информация за версията"""
    version_info = '''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(1, 2, 0, 0),
    prodvers=(1, 2, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'OptioRoute'),
        StringStruct(u'FileDescription', u'CVRP Optimizer - Оптимизация на маршрути'),
        StringStruct(u'FileVersion', u'1.2.0'),
        StringStruct(u'InternalName', u'CVRP_Optimizer'),
        StringStruct(u'LegalCopyright', u'© 2023 OptioRoute. Всички права запазени.'),
        StringStruct(u'OriginalFilename', u'CVRP_Optimizer.exe'),
        StringStruct(u'ProductName', u'CVRP Optimizer'),
        StringStruct(u'ProductVersion', u'1.2.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [0x0409, 1200])])
  ]
)
'''
    
    with open('file_version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    
    print("✅ Създаден file_version_info.txt файл")

def build_exe():
    """Компилира EXE файла"""
    print("\n🔨 Стартирам компилиране на EXE...")
    
    try:
        # Първо опитваме с .spec файла
        print("📋 Опитвам с .spec файла...")
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
        print(f"❌ Грешка при компилиране с .spec файла: {e}")
        print("🔄 Опитвам с директни опции...")
        
        try:
            # Ако .spec файлът не работи, опитваме с директни опции
            subprocess.check_call([
                sys.executable, '-m', 'PyInstaller',
                '--onefile',
                '--console',
                '--name', 'CVRP_Optimizer',
                'main_exe.py'
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
                
        except subprocess.CalledProcessError as e2:
            print(f"❌ Грешка при компилиране с директни опции: {e2}")
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
    echo ВАЖНО: Не е намерен входен файл в data\\input.xlsx
    echo Моля, поставете входния файл в директорията data\\input.xlsx
    echo или директно в текущата директория като input.xlsx
    echo.
    echo Програмата ще се опита да стартира с наличните файлове...
    CVRP_Optimizer.exe
)

REM Програмата сама ще пита за повторно стартиране
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
    
    # 2.1 Създаваме файл с информация за версията
    create_version_info()
    
    # 3. Компилираме EXE
    if build_exe():
        # 4. Създаваме .bat файл
        create_batch_file()
        
        print("\n🎉 Създаването на EXE файла завърши успешно!")
        print("\n📋 Следващи стъпки:")
        print("1. Копирайте dist/CVRP_Optimizer.exe в желаната директория")
        print("2. Създайте data/input.xlsx файл с вашите данни в СЪЩАТА директория, където е EXE файлът")
        print("3. За да активирате SPECIAL_BUS, променете enabled=True в config.py")
        print("4. Стартирайте CVRP_Optimizer.exe или start_cvrp.bat")
        print("\n⚠️ ВАЖНО: Входният файл трябва да е в директорията 'data' в СЪЩАТА папка, където е EXE файлът")
        
    else:
        print("\n❌ Създаването на EXE файла се провали!")

if __name__ == "__main__":
    main() 