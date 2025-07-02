"""
Debug скрипт за проследяване на разпределението склад/OR-Tools
"""

from input_handler import InputHandler
from warehouse_manager import WarehouseManager
from config import get_config

def debug_allocation():
    """Проследява детайлно разпределението на клиенти"""
    print("🔍 DEBUG НА РАЗПРЕДЕЛЕНИЕ СКЛАД/OR-TOOLS")
    print("=" * 60)
    
    # Зареждаме данните
    input_handler = InputHandler()
    input_data = input_handler.load_data("data/input.xlsx")
    
    print(f"📊 ВХОДНИ ДАННИ:")
    print(f"   Общо клиенти: {len(input_data.customers)}")
    print(f"   Общ обем: {input_data.total_volume:.2f} ст.")
    
    # Изчисляваме капацитета на превозните средства
    config = get_config()
    total_capacity = 0
    print(f"\n🚛 КАПАЦИТЕТ НА ПРЕВОЗНИ СРЕДСТВА:")
    
    if config.vehicles:
        for vehicle in config.vehicles:
            if vehicle.enabled:
                vehicle_capacity = vehicle.capacity * vehicle.count
                total_capacity += vehicle_capacity
                print(f"   {vehicle.vehicle_type.value}: {vehicle.count} × {vehicle.capacity} = {vehicle_capacity} ст.")
    
    print(f"   📊 ОБЩО КАПАЦИТЕТ: {total_capacity} ст.")
    print(f"   📈 Съотношение обем/капацитет: {input_data.total_volume/total_capacity:.1%}")
    
    # Анализираме логиката
    warehouse_manager = WarehouseManager()
    
    # Сортираме клиентите
    sorted_customers = sorted(input_data.customers, key=lambda c: c.volume)
    print(f"\n📋 СОРТИРАНИ КЛИЕНТИ ПО ОБЕМ (малък → голям):")
    for i, customer in enumerate(sorted_customers[:10]):  # показваме първите 10
        print(f"   {i+1:2}. {customer.id}: {customer.volume:.1f} ст.")
    if len(sorted_customers) > 10:
        print(f"   ... и още {len(sorted_customers)-10} клиента")
    
    # Проследяваме разпределението стъпка по стъпка
    print(f"\n🔄 ПРОЦЕС НА РАЗПРЕДЕЛЕНИЕ:")
    vehicle_customers = []
    warehouse_customers = []
    current_volume = 0.0
    
    for i, customer in enumerate(sorted_customers):
        will_fit = (current_volume + customer.volume <= total_capacity)
        
        if will_fit:
            vehicle_customers.append(customer)
            current_volume += customer.volume
            destination = "ПРЕВОЗНИ СРЕДСТВА"
        else:
            warehouse_customers.append(customer)
            destination = "СКЛАД"
        
        if i < 20 or not will_fit:  # показваме първите 20 + всички които отиват в склада
            print(f"   {i+1:3}. {customer.id}: {customer.volume:6.1f} ст. → {destination}")
            print(f"        Обем до момента: {current_volume:6.1f}/{total_capacity} ст.")
            
            if not will_fit:
                print(f"        ⚠️ Надвишен капацитет с {customer.volume:.1f} ст.")
    
    # Финален резултат
    warehouse_volume = sum(c.volume for c in warehouse_customers)
    
    print(f"\n📊 ФИНАЛЕН РЕЗУЛТАТ:")
    print(f"   🚛 ЗА ПРЕВОЗНИ СРЕДСТВА:")
    print(f"       Клиенти: {len(vehicle_customers)}")
    print(f"       Обем: {current_volume:.2f} ст.")
    print(f"       Използване: {current_volume/total_capacity:.1%}")
    
    print(f"   🏭 ЗА СКЛАД:")
    print(f"       Клиенти: {len(warehouse_customers)}")
    print(f"       Обем: {warehouse_volume:.2f} ст.")
    
    print(f"\n❗ ПРОБЛЕМ В ЛОГИКАТА:")
    if len(warehouse_customers) > 0:
        print(f"   Има {len(warehouse_customers)} клиента в склада")
        print(f"   OR-Tools ще обработва само {len(vehicle_customers)} клиента")
        print(f"   Останалите {len(warehouse_customers)} клиента няма да бъдат оптимизирани!")
        
        # Анализ на проблема
        available_space = total_capacity - current_volume
        print(f"\n🔧 ВЪЗМОЖНА ОПТИМИЗАЦИЯ:")
        print(f"   Свободно място: {available_space:.2f} ст.")
        
        # Проверяваме кои клиенти от склада могат да влязат
        can_move = []
        for customer in warehouse_customers:
            if customer.volume <= available_space:
                can_move.append(customer)
        
        if can_move:
            print(f"   Могат да се преместят от склада: {len(can_move)} клиента")
            for customer in can_move[:5]:
                print(f"     - {customer.id}: {customer.volume:.1f} ст.")
    else:
        print(f"   ✅ Всички клиенти отиват в OR-Tools за оптимизация")

def test_optimized_allocation():
    """Тества оптимизираната логика"""
    print(f"\n🧪 ТЕСТ НА ОПТИМИЗИРАНАТА ЛОГИКА:")
    print("=" * 50)
    
    input_handler = InputHandler()
    input_data = input_handler.load_data("data/input.xlsx")
    
    warehouse_manager = WarehouseManager()
    allocation = warehouse_manager.allocate_customers(input_data)
    
    print(f"📊 ПРЕДИ ОПТИМИЗАЦИЯ:")
    print(f"   Превозни средства: {len(allocation.vehicle_customers)} клиента")
    print(f"   Склад: {len(allocation.warehouse_customers)} клиента")
    
    optimized_allocation = warehouse_manager.optimize_allocation(allocation)
    
    print(f"📊 СЛЕД ОПТИМИЗАЦИЯ:")
    print(f"   Превозни средства: {len(optimized_allocation.vehicle_customers)} клиента")
    print(f"   Склад: {len(optimized_allocation.warehouse_customers)} клиента")
    
    improvement = len(optimized_allocation.vehicle_customers) - len(allocation.vehicle_customers)
    if improvement > 0:
        print(f"   ✅ Подобрение: +{improvement} клиента към OR-Tools")
    else:
        print(f"   ℹ️ Без промяна в разпределението")

if __name__ == "__main__":
    debug_allocation()
    test_optimized_allocation() 