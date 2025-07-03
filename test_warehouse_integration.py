#!/usr/bin/env python3
"""
Тест за интеграция на warehouse логиката в OR-Tools
"""

from config import get_config, config_manager
from input_handler import InputHandler
from cvrp_solver import CVRPSolver

def test_warehouse_integration():
    """Тества новия подход - OR-Tools сам решава за склада"""
    print("🚀 ТЕСТ ЗА WAREHOUSE ИНТЕГРАЦИЯ В OR-TOOLS")
    print("=" * 60)
    
    try:
        # Зареждаме конфигурацията
        config = get_config()
        
        print(f"📋 КОНФИГУРАЦИЯ:")
        print(f"   Warehouse enabled: {config.warehouse.enable_warehouse}")
        print(f"   OR-Tools time limit: {config.cvrp.time_limit_seconds} сек")
        
        # Показваме автобусите
        print(f"\n🚛 КОНФИГУРАЦИЯ НА АВТОБУСИ:")
        for i, vehicle in enumerate(config.vehicles):
            if vehicle.enabled:
                print(f"   {i+1}. {vehicle.vehicle_type.value}: {vehicle.count} бр, {vehicle.capacity} ст, {vehicle.max_distance_km} км")
        
        # Зареждаме данните
        print(f"\n📊 ЗАРЕЖДАНЕ НА ДАННИ:")
        input_handler = InputHandler()
        input_data = input_handler.load_data()
        
        print(f"   Общо клиенти: {len(input_data.customers)}")
        print(f"   Общ обем: {input_data.total_volume:.2f} ст.")
        
        # Създаваме CVRP solver
        cvrp_solver = CVRPSolver()
        
        print(f"\n🔧 СТАРТИРАНЕ НА OR-TOOLS С ВСИЧКИ КЛИЕНТИ:")
        print("   OR-Tools ще реши сам кои клиенти да отидат в склада!")
        
        # Използваме новия метод - всички клиенти
        solution = cvrp_solver.solve_with_all_customers(
            all_customers=input_data.customers,
            depot_location=input_data.depot_location
        )
        
        print(f"\n✅ РЕЗУЛТАТ:")
        print(f"   Използвани автобуси: {solution.total_vehicles_used}")
        print(f"   Общо разстояние: {solution.total_distance_km:.2f} км")
        print(f"   Общо време: {solution.total_time_minutes:.1f} мин")
        print(f"   Допустимо решение: {'Да' if solution.is_feasible else 'Не'}")
        
        # Анализ на маршрутите
        print(f"\n📈 АНАЛИЗ НА МАРШРУТИТЕ:")
        warehouse_customers = []
        vehicle_customers = []
        
        for route in solution.routes:
            if route.vehicle_type.value == 'warehouse':
                warehouse_customers.extend(route.customers)
                print(f"   🏭 WAREHOUSE маршрут: {len(route.customers)} клиента, {route.total_volume:.2f} ст.")
            else:
                vehicle_customers.extend(route.customers)
                print(f"   🚛 {route.vehicle_type.value.upper()}: {len(route.customers)} клиента, {route.total_volume:.2f} ст., {route.total_distance_km:.1f} км")
        
        print(f"\n📊 ФИНАЛНО РАЗПРЕДЕЛЕНИЕ:")
        print(f"   Клиенти в автобуси: {len(vehicle_customers)}")
        print(f"   Клиенти в склада: {len(warehouse_customers)}")
        print(f"   Общ обем автобуси: {sum(c.volume for c in vehicle_customers):.2f} ст.")
        print(f"   Общ обем склад: {sum(c.volume for c in warehouse_customers):.2f} ст.")
        
        # Проверка за валидност
        total_input = len(input_data.customers)
        total_output = len(vehicle_customers) + len(warehouse_customers)
        
        if total_input == total_output:
            print(f"✅ Валидност: Всички клиенти са разпределени ({total_input} = {total_output})")
        else:
            print(f"❌ Грешка: Липсват клиенти ({total_input} != {total_output})")
        
        cvrp_solver.close()
        return True
        
    except Exception as e:
        print(f"❌ Грешка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_warehouse_integration()
    if success:
        print("\n✅ Тестът завърши успешно!")
    else:
        print("\n❌ Тестът завърши с грешки!") 