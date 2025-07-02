"""
Тест скрипт за проверка на OR-Tools интеграцията
"""

def test_ortools_import():
    """Тества дали OR-Tools може да се импортира"""
    try:
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
        print("✅ OR-Tools е успешно инсталиран и може да се импортира")
        return True
    except ImportError as e:
        print(f"❌ OR-Tools не може да се импортира: {e}")
        print("💡 Инсталирайте OR-Tools с: pip install ortools")
        return False

def test_config():
    """Тества новата конфигурация"""
    try:
        from config import get_config
        config = get_config()
        
        print(f"✅ Конфигурация заредена успешно")
        print(f"📊 Алгоритъм: {config.cvrp.algorithm}")
        print(f"⏱️ Време лимит: {config.cvrp.time_limit_seconds} секунди")
        print(f"🎯 Първа стратегия: {config.cvrp.first_solution_strategy}")
        print(f"🔍 Локално търсене: {config.cvrp.local_search_metaheuristic}")
        
        return True
    except Exception as e:
        print(f"❌ Грешка при тестване на конфигурацията: {e}")
        return False

def test_cvrp_solver_import():
    """Тества дали CVRP solver може да се импортира"""
    try:
        from cvrp_solver import CVRPSolver, ORToolsSolver
        print("✅ CVRP Solver и OR-Tools Solver могат да се импортират")
        return True
    except Exception as e:
        print(f"❌ Грешка при импортиране на CVRP solver: {e}")
        return False

def test_simple_solve():
    """Тества опростено решаване на CVRP"""
    try:
        from cvrp_solver import CVRPSolver
        from warehouse_manager import WarehouseAllocation
        from input_handler import Customer
        
        # Създаване на примерни данни
        customers = [
            Customer("C1", "Client 1", (42.7, 23.3), 50, "42.7, 23.3"),
            Customer("C2", "Client 2", (42.71, 23.31), 30, "42.71, 23.31"),
            Customer("C3", "Client 3", (42.69, 23.29), 40, "42.69, 23.29")
        ]
        
        allocation = WarehouseAllocation(
            vehicle_customers=customers,
            warehouse_customers=[],
            total_vehicle_capacity=1000,
            total_vehicle_volume=120,
            warehouse_volume=0,
            capacity_utilization=0.12
        )
        
        depot_location = (42.695785029219415, 23.23165887245312)
        
        solver = CVRPSolver()
        solution = solver.solve(allocation, depot_location)
        solver.close()
        
        print(f"✅ CVRP тест успешен!")
        print(f"🚛 Използвани превозни средства: {solution.total_vehicles_used}")
        print(f"📏 Общо разстояние: {solution.total_distance_km:.2f} км")
        print(f"⏰ Общо време: {solution.total_time_minutes:.1f} минути")
        
        return True
        
    except Exception as e:
        print(f"❌ Грешка при тестване на CVRP решаване: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Стартира всички тестове"""
    print("🧪 Тестване на OR-Tools интеграция")
    print("=" * 50)
    
    tests = [
        ("OR-Tools импорт", test_ortools_import),
        ("Конфигурация", test_config),
        ("CVRP Solver импорт", test_cvrp_solver_import),
        ("Опростено решаване", test_simple_solve)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔹 Тест: {test_name}")
        print("-" * 30)
        
        if test_func():
            passed += 1
        else:
            print("⚠️ Тестът не премина")
    
    print("\n" + "=" * 50)
    print(f"📊 Резултати: {passed}/{total} тестове преминаха")
    
    if passed == total:
        print("🎉 Всички тестове преминаха! OR-Tools интеграцията работи правилно.")
    else:
        print("⚠️ Някои тестове не преминаха. Моля проверете инсталацията.")

if __name__ == "__main__":
    main() 