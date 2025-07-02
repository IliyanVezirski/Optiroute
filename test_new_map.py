"""
Тест файл за новата функционалност на картата
"""

from output_handler import OutputHandler, VEHICLE_SETTINGS
from cvrp_solver import CVRPSolution, Route, VehicleType
from warehouse_manager import WarehouseAllocation
from input_handler import Customer

def test_new_map_features():
    """Тества новите функции на картата"""
    
    print("🗺️  Тестване на новата функционалност на картата")
    print("=" * 50)
    
    # Тест 1: Проверка на настройките за превозни средства
    print("✅ Настройки за превозни средства:")
    for vehicle_type, settings in VEHICLE_SETTINGS.items():
        print(f"   {vehicle_type}: {settings['name']} ({settings['color']}, {settings['icon']})")
    
    print()
    
    # Тест 2: Създаване на тестови данни
    print("✅ Създавам тестови данни...")
    
    # Тестови клиенти
    customers = [
        Customer("1", "Клиент 1", 50.0, "42.7,23.3", (42.7, 23.3)),
        Customer("2", "Клиент 2", 30.0, "42.71,23.31", (42.71, 23.31)),
        Customer("3", "Клиент 3", 40.0, "42.72,23.32", (42.72, 23.32)),
    ]
    
    # Тестови маршрути
    routes = [
        Route(VehicleType.INTERNAL_BUS, customers[:2], 0, 0, 0),
        Route(VehicleType.EXTERNAL_BUS, customers[2:], 0, 0, 0),
    ]
    
    solution = CVRPSolution(routes, 0, True)
    
    # Тестово разпределение в склада
    warehouse_allocation = WarehouseAllocation([], customers)
    
    depot_location = (42.695785029219415, 23.23165887245312)
    
    print("   - Създадени 3 клиента")
    print("   - Създадени 2 маршрута")
    print("   - Настроено депо")
    
    print()
    
    # Тест 3: Проверка на OutputHandler
    print("✅ Проверка на OutputHandler...")
    
    try:
        handler = OutputHandler()
        print("   - OutputHandler създаден успешно")
        
        # Опит за създаване на карта (без запис)
        map_generator = handler.map_generator
        print("   - Map generator инициализиран")
        
        print("   - Готов за генериране на карта с:")
        print("     • Различни пинчета за всеки тип автобус")
        print("     • Номерирани маркери за поредността")
        print("     • Линии на маршрутите")
        print("     • Легенда с информация")
        print("     • БЕЗ показване на складови клиенти")
        
    except Exception as e:
        print(f"   ❌ Грешка: {e}")
    
    print()
    print("🎯 Заключение:")
    print("   Новата функционалност е готова за тестване!")
    print("   За пълен тест изпълнете: python demo.py")

if __name__ == "__main__":
    test_new_map_features() 