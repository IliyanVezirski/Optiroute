#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Анализ на разпределението за debugging
"""

from input_handler import load_customer_data
from warehouse_manager import WarehouseManager

def main():
    print("=== АНАЛИЗ НА РАЗПРЕДЕЛЕНИЕТО ===")
    
    # Зареждане на данните
    data = load_customer_data('data/input.xlsx')
    wm = WarehouseManager()
    allocation = wm.allocate_customers(data)
    
    print(f"Общо клиенти в input: {len(data.customers)}")
    print(f"Общ обем в input: {data.total_volume:.1f}ст")
    print()
    
    print(f"Клиенти за автобуси: {len(allocation.vehicle_customers)}")
    vehicle_volume = sum(c.volume for c in allocation.vehicle_customers)
    print(f"Обем за автобуси: {vehicle_volume:.1f}ст")
    print()
    
    print(f"Клиенти за склад: {len(allocation.warehouse_customers)}")
    warehouse_volume = sum(c.volume for c in allocation.warehouse_customers)
    print(f"Обем за склад: {warehouse_volume:.1f}ст")
    print()
    
    print(f"Капацитет автобуси: {allocation.total_vehicle_capacity}ст")
    print(f"Използван капацитет: {allocation.total_vehicle_volume:.1f}ст")
    print(f"Capacity utilization: {allocation.capacity_utilization*100:.1f}%")
    print()
    
    print("=== ПРОБЛЕМНА ЗОНА ===")
    
    if vehicle_volume > allocation.total_vehicle_capacity:
        print(f"❌ ПРОБЛЕМ: Обемът за автобуси ({vehicle_volume:.1f}ст) НАДВИШАВА капацитета ({allocation.total_vehicle_capacity}ст)")
        print(f"   Надвишение: {vehicle_volume - allocation.total_vehicle_capacity:.1f}ст")
    else:
        print(f"✅ OK: Обемът за автобуси ({vehicle_volume:.1f}ст) ПО-МАЛЪК от капацитета ({allocation.total_vehicle_capacity}ст)")
    
    total_check = vehicle_volume + warehouse_volume
    print(f"Проверка общ обем: {vehicle_volume:.1f} + {warehouse_volume:.1f} = {total_check:.1f}ст")
    print(f"Трябва да е равно на input обем: {data.total_volume:.1f}ст")
    
    if abs(total_check - data.total_volume) > 0.1:
        print("❌ ПРОБЛЕМ: Загуба на данни при разпределението!")
    else:
        print("✅ OK: Данните са запазени при разпределението")

if __name__ == "__main__":
    main() 