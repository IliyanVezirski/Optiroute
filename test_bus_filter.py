"""
Тест за филтъра на бусовете в output_handler
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from output_handler import InteractiveMapGenerator
from config import get_config
import logging

# Настройваме logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_bus_filter():
    """Тества филтъра на бусовете"""
    print("🧪 Тествам филтъра на бусовете...")
    
    # Създаваме map generator
    config = get_config().output
    map_generator = InteractiveMapGenerator(config)
    
    # Създаваме тестови данни
    from cvrp_solver import Route, Customer, VehicleType
    from typing import List
    
    # Тестови клиенти
    customers = [
        Customer(id="1", name="Клиент 1", volume=10.0, coordinates=(42.697735, 23.321589), original_gps_data="42.697735,23.321589"),
        Customer(id="2", name="Клиент 2", volume=15.0, coordinates=(42.695785, 23.231659), original_gps_data="42.695785,23.231659"),
        Customer(id="3", name="Клиент 3", volume=8.0, coordinates=(42.699735, 23.331589), original_gps_data="42.699735,23.331589"),
        Customer(id="4", name="Клиент 4", volume=12.0, coordinates=(42.693785, 23.221659), original_gps_data="42.693785,23.221659"),
        Customer(id="5", name="Клиент 5", volume=20.0, coordinates=(42.691785, 23.211659), original_gps_data="42.691785,23.211659"),
        Customer(id="6", name="Клиент 6", volume=18.0, coordinates=(42.689785, 23.201659), original_gps_data="42.689785,23.201659"),
    ]
    
    # Създаваме тестови маршрути
    routes = [
        Route(
            vehicle_type=VehicleType.CENTER_BUS,
            customers=customers[:2],
            total_distance_km=25.5,
            total_time_minutes=45,
            total_volume=25.0,
            vehicle_id="center_bus_1",
            depot_location=(42.697735, 23.321589)
        ),
        Route(
            vehicle_type=VehicleType.INTERNAL_BUS,
            customers=customers[2:4],
            total_distance_km=18.2,
            total_time_minutes=32,
            total_volume=20.0,
            vehicle_id="internal_bus_1",
            depot_location=(42.697735, 23.321589)
        ),
        Route(
            vehicle_type=VehicleType.EXTERNAL_BUS,
            customers=customers[4:],
            total_distance_km=30.1,
            total_time_minutes=55,
            total_volume=38.0,
            vehicle_id="external_bus_1",
            depot_location=(42.697735, 23.321589)
        )
    ]
    
    # Създаваме тестово решение
    from cvrp_solver import CVRPSolution, WarehouseAllocation
    solution = CVRPSolution(
        routes=routes,
        total_distance_km=73.8,
        total_time_minutes=132,
        total_vehicles_used=3,
        fitness_score=73.8,
        is_feasible=True
    )
    warehouse_allocation = WarehouseAllocation(
        warehouse_customers=[],
        vehicle_customers=customers,
        total_vehicle_capacity=100.0,
        total_vehicle_volume=73.0,
        warehouse_volume=0.0,
        capacity_utilization=0.73
    )
    
    print(f"📊 Създадох {len(routes)} тестови маршрута:")
    for i, route in enumerate(routes):
        print(f"   🚌 Автобус {i+1}: {len(route.customers)} клиента, {route.total_distance_km:.1f} км")
    
    # Създаваме картата
    print("\n🗺️ Създавам интерактивна карта с филтър...")
    route_map = map_generator.create_map(solution, warehouse_allocation, (42.697735, 23.321589))
    
    # Записваме картата
    map_file = map_generator.save_map(route_map, "test_bus_filter_map.html")
    print(f"✅ Картата е записана в: {map_file}")
    
    print("\n🎯 Функции на филтъра:")
    print("   • В горния десен ъгъл има контрол за слоеве")
    print("   • Можеш да включиш/изключиш всеки автобус поотделно")
    print("   • Всички маркери и линии на автобуса се показват/скриват заедно")
    print("   • Легендата в левия ъгъл показва статистики")
    
    return map_file

if __name__ == "__main__":
    test_bus_filter() 