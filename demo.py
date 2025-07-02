"""
Демонстрационен скрипт за CVRP програмата
Показва как да се използват различните функционалности
"""

import os
import sys
from create_sample_data import create_sample_excel
from main import CVRPApplication

def run_demo():
    """Стартира пълна демонстрация на CVRP програмата"""
    
    print("=" * 70)
    print("🚛 CVRP OPTIMIZER - ДЕМОНСТРАЦИЯ")
    print("=" * 70)
    
    # Стъпка 1: Създаване на примерни данни
    print("\n📊 Стъпка 1: Създаване на примерни данни")
    print("-" * 50)
    
    sample_file = create_sample_excel()
    
    # Стъпка 2: Стартиране на основната програма
    print("\n🔧 Стъпка 2: Стартиране на CVRP оптимизация")
    print("-" * 50)
    
    app = CVRPApplication()
    success = app.run(sample_file)
    
    if success:
        print("\n✅ Демонстрацията завърши успешно!")
        print("\n📁 Генерирани файлове:")
        
        # Проверяваме генерираните файлове
        output_files = [
            "output/interactive_map.html",
            "output/excel/warehouse_orders.xlsx",
            "output/excel/vehicle_routes.xlsx",
            "logs/cvrp.log"
        ]
        
        for file_path in output_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✓ {file_path} ({size} bytes)")
            else:
                print(f"  ✗ {file_path} (не е създаден)")
        
        print("\n🗺️  За да видите резултатите:")
        print("  1. Отворете output/interactive_map.html в браузър")
        print("  2. Прегледайте Excel файловете в output/excel/")
        print("  3. Проверете лога в logs/cvrp.log")
        
    else:
        print("\n❌ Демонстрацията завърши с грешки!")
        print("Моля проверете лог файла за детайли.")
    
    return success

def run_custom_demo():
    """Демонстрация с персонализирани настройки"""
    
    print("\n" + "=" * 70)
    print("⚙️  CVRP OPTIMIZER - ПЕРСОНАЛИЗИРАНА ДЕМОНСТРАЦИЯ")
    print("=" * 70)
    
    # Създаваме примерни данни ако не съществуват
    sample_file = "data/sample_clients.xlsx"
    if not os.path.exists(sample_file):
        print("📊 Създаване на примерни данни...")
        sample_file = create_sample_excel()
    
    # Персонализирани настройки
    custom_config = {
        "cvrp": {
            "time_limit_seconds": 60,  # 1 минута лимит за демо
            "log_search": True,        # показва прогреса
            "first_solution_strategy": "PATH_CHEAPEST_ARC"
        },
        "osrm": {
            "chunk_size": 25,         # По-малки chunks
            "use_cache": True
        },
        "warehouse": {
            "sort_by_volume": True,
            "move_largest_to_warehouse": True
        },
        "output": {
            "enable_interactive_map": True,
            "show_route_colors": True,
            "include_detailed_info": True
        },
        "debug_mode": True
    }
    
    print("⚙️  Използвани настройки:")
    for section, settings in custom_config.items():
        print(f"  {section}:")
        for key, value in settings.items():
            print(f"    {key}: {value}")
    
    print(f"\n🚀 Стартиране с персонализирани настройки...")
    
    app = CVRPApplication()
    success = app.run_with_custom_config(custom_config, sample_file)
    
    return success

def demo_vehicle_configurations():
    """Демонстрира различни конфигурации на превозни средства"""
    
    print("\n" + "=" * 70)
    print("🚚 ДЕМОНСТРАЦИЯ НА РАЗЛИЧНИ КОНФИГУРАЦИИ ПРЕВОЗНИ СРЕДСТВА")
    print("=" * 70)
    
    from config import VehicleType, config_manager
    
    # Конфигурация 1: Само вътрешни бусове
    print("\n🔧 Конфигурация 1: Само вътрешни бусове")
    config1 = {
        "vehicles": [
            {"vehicle_type": "internal_bus", "enabled": True},
            {"vehicle_type": "center_bus", "enabled": False},
            {"vehicle_type": "external_bus", "enabled": False}
        ]
    }
    
    # Конфигурация 2: Само външни бусове
    print("🔧 Конфигурация 2: Само външни бусове")
    config2 = {
        "vehicles": [
            {"vehicle_type": "internal_bus", "enabled": False},
            {"vehicle_type": "center_bus", "enabled": False},
            {"vehicle_type": "external_bus", "enabled": True}
        ]
    }
    
    # Конфигурация 3: Всички типове
    print("🔧 Конфигурация 3: Всички типове превозни средства")
    config3 = {
        "vehicles": [
            {"vehicle_type": "internal_bus", "enabled": True},
            {"vehicle_type": "center_bus", "enabled": True},
            {"vehicle_type": "external_bus", "enabled": True}
        ]
    }
    
    configurations = [
        ("Само вътрешни бусове", config1),
        ("Само външни бусове", config2),
        ("Всички типове", config3)
    ]
    
    sample_file = "data/sample_clients.xlsx"
    if not os.path.exists(sample_file):
        sample_file = create_sample_excel()
    
    for name, config in configurations:
        print(f"\n📊 Тестване конфигурация: {name}")
        print("-" * 50)
        
        app = CVRPApplication()
        success = app.run_with_custom_config(config, sample_file)
        
        if success:
            print(f"✅ {name} - успешно")
        else:
            print(f"❌ {name} - неуспешно")

def main():
    """Главна функция за демонстрацията"""
    
    # Създаваме необходимите директории
    directories = ["data", "output", "output/excel", "output/charts", "logs", "cache"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("🎯 Изберете демонстрация:")
    print("1. Основна демонстрация")
    print("2. Персонализирана демонстрация") 
    print("3. Демонстрация на различни конфигурации превозни средства")
    print("4. Всички демонстрации")
    
    choice = input("\nВъведете номер (1-4): ").strip()
    
    if choice == "1":
        run_demo()
    elif choice == "2":
        run_custom_demo()
    elif choice == "3":
        demo_vehicle_configurations()
    elif choice == "4":
        print("🚀 Стартиране на всички демонстрации...")
        run_demo()
        run_custom_demo()
        demo_vehicle_configurations()
    else:
        print("❌ Невалиден избор. Стартирам основната демонстрация...")
        run_demo()

if __name__ == "__main__":
    main() 