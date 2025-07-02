"""
Тест на подобрената allocation логика
"""

def test_allocation_improvement():
    """Тества подобрената логика за разпределение"""
    print("🧪 ТЕСТ НА ПОДОБРЕНАТА ALLOCATION ЛОГИКА")
    print("=" * 60)
    
    try:
        from input_handler import InputHandler
        from warehouse_manager import WarehouseManager
        from config import get_config
        
        # Зареждаме данните
        input_handler = InputHandler()
        input_data = input_handler.load_data("data/input.xlsx")
        
        # Изчисляваме капацитета
        config = get_config()
        total_capacity = 0
        if config.vehicles:
            for vehicle in config.vehicles:
                if vehicle.enabled:
                    total_capacity += vehicle.capacity * vehicle.count
        
        print(f"📊 ПРЕГЛЕД НА ДАННИТЕ:")
        print(f"   Общо клиенти: {len(input_data.customers)}")
        print(f"   Общ обем: {input_data.total_volume:.2f} ст.")
        print(f"   Капацитет превозни средства: {total_capacity} ст.")
        print(f"   Съотношение: {input_data.total_volume/total_capacity:.1%}")
        
        # Тестваме новата логика
        warehouse_manager = WarehouseManager()
        allocation = warehouse_manager.allocate_customers(input_data)
        
        print(f"\n🔄 РЕЗУЛТАТ ОТ ПОДОБРЕНАТА ЛОГИКА:")
        print(f"   🚛 За превозни средства: {len(allocation.vehicle_customers)} клиента")
        print(f"       Обем: {allocation.total_vehicle_volume:.2f} ст.")
        print(f"       Използване: {allocation.capacity_utilization:.1%}")
        
        print(f"   🏭 За склад: {len(allocation.warehouse_customers)} клиента") 
        print(f"       Обем: {allocation.warehouse_volume:.2f} ст.")
        
        # Проверяваме дали е по-добре от простата логика
        simple_allocation = test_simple_logic(input_data.customers, total_capacity)
        
        print(f"\n📈 СРАВНЕНИЕ С ПРОСТАТА ЛОГИКА:")
        improvement = len(allocation.vehicle_customers) - simple_allocation[0]
        if improvement > 0:
            print(f"   ✅ Подобрение: +{improvement} клиента за OR-Tools")
            print(f"   🎯 Повече клиенти ще бъдат оптимизирани!")
        elif improvement < 0:
            print(f"   ⚠️ Влошение: {improvement} клиента")
        else:
            print(f"   ➡️ Същия резултат")
        
        capacity_improvement = allocation.capacity_utilization - simple_allocation[1]
        print(f"   📊 Използване на капацитета: {capacity_improvement:+.1%}")
        
        return allocation
        
    except Exception as e:
        print(f"❌ Грешка в теста: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_simple_logic(customers, total_capacity):
    """Тества простата логика за сравнение"""
    sorted_customers = sorted(customers, key=lambda c: c.volume)
    
    vehicle_count = 0
    current_volume = 0.0
    
    for customer in sorted_customers:
        if current_volume + customer.volume <= total_capacity:
            vehicle_count += 1
            current_volume += customer.volume
        else:
            break
    
    utilization = current_volume / total_capacity if total_capacity > 0 else 0
    return vehicle_count, utilization

def show_top_customers_for_ortools(allocation):
    """Показва кои клиенти отиват в OR-Tools"""
    if not allocation:
        return
        
    print(f"\n👥 КЛИЕНТИ ЗА OR-TOOLS ОПТИМИЗАЦИЯ:")
    print("=" * 50)
    
    # Сортираме по обем
    sorted_vehicle_customers = sorted(allocation.vehicle_customers, key=lambda c: c.volume, reverse=True)
    
    print(f"📊 Общо клиенти за OR-Tools: {len(sorted_vehicle_customers)}")
    print(f"📋 Топ 15 най-големи:")
    
    for i, customer in enumerate(sorted_vehicle_customers[:15]):
        print(f"   {i+1:2}. {customer.id}: {customer.volume:6.1f} ст. - {customer.name}")
    
    if len(sorted_vehicle_customers) > 15:
        print(f"   ... и още {len(sorted_vehicle_customers)-15} клиента")
    
    # Показваме статистики
    volumes = [c.volume for c in sorted_vehicle_customers]
    print(f"\n📈 СТАТИСТИКИ:")
    print(f"   Най-голям клиент: {max(volumes):.1f} ст.")
    print(f"   Най-малък клиент: {min(volumes):.1f} ст.")
    print(f"   Среден обем: {sum(volumes)/len(volumes):.1f} ст.")

if __name__ == "__main__":
    allocation = test_allocation_improvement()
    if allocation:
        show_top_customers_for_ortools(allocation) 