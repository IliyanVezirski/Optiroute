#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config import MainConfig
import config
import importlib

def test_osrm_limits():
    """Показва актуалните OSRM лимити и настройки"""
    config = MainConfig()
    
    print("🌐 OSRM Настройки:")
    print(f"   📊 Chunk size: {config.osrm.chunk_size}")
    print(f"   ⏱️ Timeout: {config.osrm.timeout_seconds}s")
    print(f"   🔄 Retry attempts: {config.osrm.retry_attempts}")
    print(f"   🚀 Average speed: {config.osrm.average_speed_kmh} km/h")
    print()
    
    # Пресмятане за различни броя клиенти
    test_clients = [50, 100, 150, 250, 500]
    
    print("📈 Chunks за различни броя клиенти:")
    for clients in test_clients:
        chunks_per_side = (clients + config.osrm.chunk_size - 1) // config.osrm.chunk_size
        total_chunks = chunks_per_side * chunks_per_side
        print(f"   {clients:3d} клиента: {total_chunks:2d} chunks")
    
    print()
    print("⚡ Лимити:")
    print("   • Локален OSRM: ~100 локации per chunk (препоръчително)")
    print("   • Публичен OSRM GET: ~25 локации per chunk")
    print("   • Публичен OSRM POST: ~100 локации per chunk")
    print("   • Route API: 1 заявка = 1 маршрут (МНОГО БАВНО за >15 локации)")

if __name__ == "__main__":
    test_osrm_limits()

# Принудително рестартираме config
importlib.reload(config)

cfg = config.get_config()

print('=== ЛОКАЦИИ ===')
print(f'Основно депо: {cfg.locations.depot_location}')
print(f'Център локация: {cfg.locations.center_location}')

print('\n=== ПРЕВОЗНИ СРЕДСТВА ===')
for i, vehicle in enumerate(cfg.vehicles):
    print(f'{i+1}. {vehicle.vehicle_type.value}:')
    print(f'   capacity: {vehicle.capacity}')
    print(f'   count: {vehicle.count}')
    print(f'   start_location: {vehicle.start_location}')
    if vehicle.vehicle_type.value == 'center_bus':
        print(f'   📍 CENTER_BUS трябва да стартира от: {cfg.locations.center_location}')
        print(f'   ✅ Правилно настроен: {vehicle.start_location == cfg.locations.center_location}')
    print()

# Тест на enabled vehicles
enabled_vehicles = config.config_manager.get_enabled_vehicles()
print('=== ВКЛЮЧЕНИ ПРЕВОЗНИ СРЕДСТВА ===')
for vehicle in enabled_vehicles:
    print(f'{vehicle.vehicle_type.value}: start_location = {vehicle.start_location}') 