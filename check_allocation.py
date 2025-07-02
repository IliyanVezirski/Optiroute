#!/usr/bin/env python3
"""
Проверка защо всички заявки отиват в склада
"""

from config import get_config
from input_handler import InputHandler
from warehouse_manager import WarehouseManager

def main():
    print("=== ПРОВЕРКА НА РАЗПРЕДЕЛЕНИЕТО ===")
    
    # Зареждане на конфигурацията
    config = get_config()
    print(f"\n1. КОНФИГУРАЦИЯ НА АВТОБУСИТЕ:")
    
    total_capacity = 0
    if config.vehicles:
        for i, vehicle in enumerate(config.vehicles):
            if vehicle.enabled:
                vehicle_capacity = vehicle.capacity * vehicle.count
                total_capacity += vehicle_capacity
                print(f"   {vehicle.vehicle_type.value}: {vehicle.count} бр. x {vehicle.capacity} ст. = {vehicle_capacity} ст.")
            else:
                print(f"   {vehicle.vehicle_type.value}: ИЗКЛЮЧЕН")
    
    print(f"\n   ОБЩ КАПАЦИТЕТ: {total_capacity} стотинки")
    
    # Зареждане на данните
    try:
        print(f"\n2. ЗАРЕЖДАНЕ НА ДАННИ:")
        input_handler = InputHandler()
        input_data = input_handler.load_data()
        print(f"   Общо клиенти: {len(input_data.customers)}")
        print(f"   Общ обем: {input_data.total_volume:.1f} стотинки")
        print(f"   Съотношение обем/капацитет: {input_data.total_volume/total_capacity:.1%}")
        
        # Показване на първите 10 клиента по обем
        sorted_customers = sorted(input_data.customers, key=lambda c: c.volume, reverse=True)
        print(f"\n   Най-големи 10 клиента:")
        for i, customer in enumerate(sorted_customers[:10]):
            print(f"     {i+1}. Клиент {customer.id}: {customer.volume:.1f} ст.")
        
        # Проверка на алокацията
        print(f"\n3. РАЗПРЕДЕЛЕНИЕ:")
        warehouse_manager = WarehouseManager()
        allocation = warehouse_manager.allocate_customers(input_data)
        
        print(f"   🚛 За автобуси: {len(allocation.vehicle_customers)} клиента ({allocation.total_vehicle_volume:.1f} ст.)")
        print(f"   🏭 За склад: {len(allocation.warehouse_customers)} клиента ({allocation.warehouse_volume:.1f} ст.)")
        print(f"   📊 Използване: {allocation.capacity_utilization:.1%}")
        
        # Ако всички са в склада, покажи защо
        if len(allocation.vehicle_customers) == 0:
            print(f"\n❌ ПРОБЛЕМ: Всички клиенти са в склада!")
            print(f"   Възможни причини:")
            print(f"   - Общият обем ({input_data.total_volume:.1f}) > капацитета ({total_capacity})")
            print(f"   - Грешка в логиката на алокация")
            print(f"   - Автобусите са изключени")
        
        elif len(allocation.warehouse_customers) == 0:
            print(f"\n✅ Всички клиенти са за автобуси")
        
        else:
            print(f"\n✅ Нормално разпределение")
            
        # Детайли за warehouse конфигурацията
        print(f"\n4. WAREHOUSE КОНФИГУРАЦИЯ:")
        print(f"   enable_warehouse: {config.warehouse.enable_warehouse}")
        print(f"   move_largest_to_warehouse: {config.warehouse.move_largest_to_warehouse}")
        print(f"   sort_by_volume: {config.warehouse.sort_by_volume}")
        
    except Exception as e:
        print(f"❌ Грешка при зареждане на данни: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 