"""
EXE входна точка за CVRP програма
Този файл се използва за създаване на EXE файл с PyInstaller
"""

import sys
import os
import logging
import shutil
from pathlib import Path
import importlib.util

def setup_exe_environment():
    """Настройва средата за EXE изпълнение"""
    # Променяме работната директория към директорията на EXE файла
    if getattr(sys, 'frozen', False):
        # Ако е EXE файл, използваме директорията на EXE файла
        exe_dir = Path(sys.executable).parent
        os.chdir(exe_dir)
        print(f"📁 Работна директория: {exe_dir}")
    else:
        # Ако е Python скрипт, използваме директорията на скрипта
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        print(f"📁 Работна директория: {script_dir}")
    
    # Създаваме необходимите директории ако не съществуват
    directories = ['logs', 'output', 'cache', 'data']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # Настройваме logging за EXE
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/cvrp_exe.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def copy_output_files():
    """Копира изходните файлове от временната папка в директорията на EXE"""
    try:
        # Намираме временната папка на PyInstaller
        if getattr(sys, 'frozen', False):
            # За EXE файл, временната папка е _MEI* в temp
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            me_dirs = list(temp_dir.glob('_MEI*'))
            
            if me_dirs:
                # Вземаме най-новия _MEI* директорий
                temp_me_dir = max(me_dirs, key=lambda x: x.stat().st_mtime)
                temp_output_dir = temp_me_dir / 'output'
                
                if temp_output_dir.exists():
                    print(f"📁 Копирам файлове от временната папка: {temp_output_dir}")
                    
                    # Копираме всички файлове от временната output папка
                    local_output_dir = Path('output')
                    local_output_dir.mkdir(exist_ok=True)
                    
                    for item in temp_output_dir.rglob('*'):
                        if item.is_file():
                            # Изчисляваме относителния път
                            relative_path = item.relative_to(temp_output_dir)
                            target_path = local_output_dir / relative_path
                            
                            # Създаваме директориите ако не съществуват
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Копираме файла
                            shutil.copy2(item, target_path)
                            print(f"  ✅ Копиран: {relative_path}")
                    
                    print(f"📁 Всички файлове са копирани в: {local_output_dir.absolute()}")
                else:
                    print("⚠️ Не са намерени изходни файлове в временната папка")
            else:
                print("⚠️ Не е намерена временна папка на PyInstaller")
        else:
            print("ℹ️ Не е EXE файл - пропускам копирането")
            
    except Exception as e:
        print(f"⚠️ Грешка при копиране на файлове: {e}")

# Динамично зареждане на config.py от директорията на EXE файла
def load_config():
    if getattr(sys, 'frozen', False):
        # За EXE файл, използваме директорията на EXE файла
        exe_dir = Path(sys.executable).parent
        config_path = exe_dir / 'config.py'
    else:
        # За Python скрипт, използваме директорията на скрипта
        script_dir = Path(__file__).parent
        config_path = script_dir / 'config.py'
    
    if config_path.exists():
        spec = importlib.util.spec_from_file_location('config', str(config_path))
        if spec and spec.loader:
            config = importlib.util.module_from_spec(spec)
            sys.modules['config'] = config
            spec.loader.exec_module(config)
            print(f"✅ Конфигурация заредена от: {config_path}")
        else:
            print(f"⚠️ Не мога да заредя config.py от: {config_path}")
    else:
        print(f"⚠️ config.py не е намерен в: {config_path}")

# Добавяме директорията на EXE файла към Python path
if getattr(sys, 'frozen', False):
    exe_dir = Path(sys.executable).parent
    sys.path.insert(0, str(exe_dir))
else:
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))

# Импортираме главната функция
from main import main

def main_exe():
    """Главна функция за EXE"""
    try:
        setup_exe_environment()
        load_config()
        
        print("🚀 Стартиране на CVRP оптимизация...")
        print("=" * 50)
        
        # Проверяваме дали има входен файл като аргумент
        input_file = None
        if len(sys.argv) > 1:
            input_file = sys.argv[1]
            print(f"📁 Използвам входен файл: {input_file}")
        else:
            # Търсим подразбиращ се файл
            default_files = ['data/input.xlsx', 'input.xlsx']
            for file_path in default_files:
                if os.path.exists(file_path):
                    input_file = file_path
                    print(f"📁 Намерен входен файл: {input_file}")
                    break
            
            if not input_file:
                print("⚠️ Не е намерен входен файл. Създайте data/input.xlsx или посочете файл като аргумент.")
                print("💡 Пример: CVRP_Optimizer.exe data/my_data.xlsx")
                input("\nНатиснете Enter за да затворите програмата...")
                sys.exit(1)
        
        # Заменяме sys.argv с правилните аргументи
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]]  # Запазваме само името на програмата
        if input_file:
            sys.argv.append(input_file)
        
        # Изпълняваме главната функция
        main()
        
        # Възстановяваме оригиналните аргументи
        sys.argv = original_argv
        
        # Копираме изходните файлове
        print("\n📁 Копиране на изходните файлове...")
        copy_output_files()
        
        print("\n✅ Програмата завърши успешно!")
        print(f"📁 Резултатите са в директорията: {os.getcwd()}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Програмата е прекъсната от потребителя.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Грешка при изпълнение: {e}")
        logging.error(f"EXE грешка: {e}", exc_info=True)
        input("\nНатиснете Enter за да затворите програмата...")
        sys.exit(1)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main_exe() 