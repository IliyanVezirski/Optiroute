#!/usr/bin/env python3
"""
Диагностичен скрипт за OR-Tools проблеми
Тества различни конфигурации за да намери работещо решение
"""

import logging
from typing import List, Optional
from config import get_config
from input_handler import load_customers
from warehouse_manager import WarehouseManager
from cvrp_solver import CVRPSolver, ORToolsSolver, CVRPConfig
from osrm_client import OSRMClient

# Настройка на логирането
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ortools_minimal():
    """Тест с минимални ограничения"""
    print("�� ДИАГНОСТИКА НА OR-Tools ПРОБЛЕМИ")
    print("="*50)
    
    # Зареждане на данни
    config = get_config()
    customers = load_customers(config.data.input_file)
    
    # Разпределение между склад и автобуси
    warehouse_manager = WarehouseManager(config.warehouse)
    allocation = warehouse_manager.allocate_customers(customers)
    
    print(f"📊 Данни:")
    print(f"   Общо клиенти: {len(customers)}")
    print(f"   За автобуси: {len(allocation.vehicle_customers)}")
    print(f"   За склад: {len(allocation.warehouse_customers)}")
    
    # ТЕСТ 1: Само capacity ограничения
    print(f"\n🧪 ТЕСТ 1: Само capacity ограничения")
    test_config = CVRPConfig(
        time_limit_seconds=60,  # 1 минута
        first_solution_strategy="PATH_CHEAPEST_ARC",
        local_search_metaheuristic="AUTOMATIC",
        log_search=False
    )
    
    result1 = test_simplified_ortools(allocation, config.depot.location, test_config, only_capacity=True)
    
    # ТЕСТ 2: Увеличено време за оптимизация
    print(f"\n🧪 ТЕСТ 2: Увеличено време (10 минути)")
    test_config.time_limit_seconds = 600  # 10 минути
    result2 = test_simplified_ortools(allocation, config.depot.location, test_config, only_capacity=True)
    
    # ТЕСТ 3: Различна стратегия
    print(f"\n🧪 ТЕСТ 3: SAVINGS стратегия")
    test_config.first_solution_strategy = "SAVINGS"
    test_config.local_search_metaheuristic = "GUIDED_LOCAL_SEARCH"
    result3 = test_simplified_ortools(allocation, config.depot.location, test_config, only_capacity=True)
    
    # ТЕСТ 4: По-малко клиенти
    print(f"\n🧪 ТЕСТ 4: Тест с първите 50 клиента")
    small_allocation = type(allocation)(
        vehicle_customers=allocation.vehicle_customers[:50],
        warehouse_customers=allocation.warehouse_customers,
        total_capacity_used=sum(c.volume for c in allocation.vehicle_customers[:50])
    )
    test_config.time_limit_seconds = 300  # 5 минути
    result4 = test_simplified_ortools(small_allocation, config.depot.location, test_config, only_capacity=True)
    
    # Резултати
    print(f"\n📋 РЕЗУЛТАТИ:")
    print(f"   Тест 1 (capacity only): {'✅ УСПЕХ' if result1 else '❌ НЕУСПЕХ'}")
    print(f"   Тест 2 (10 минути): {'✅ УСПЕХ' if result2 else '❌ НЕУСПЕХ'}")
    print(f"   Тест 3 (SAVINGS): {'✅ УСПЕХ' if result3 else '❌ НЕУСПЕХ'}")
    print(f"   Тест 4 (50 клиента): {'✅ УСПЕХ' if result4 else '❌ НЕУСПЕХ'}")

def test_simplified_ortools(allocation, depot_location, test_config: CVRPConfig, only_capacity=False):
    """Тества OR-Tools с опростени ограничения"""
    try:
        # Създаване на solver с тестова конфигурация
        solver = CVRPSolver(test_config)
        
        # Създаване на custom ORToolsSolver за тестване
        customers = allocation.vehicle_customers
        osrm_client = OSRMClient()
        
        try:
            # Получаване на матрица
            locations = [depot_location] + [c.coordinates for c in customers]
            distance_matrix = osrm_client.get_distance_matrix(locations)
            
            # Получаване на включените превозни средства
            from config import config_manager
            enabled_vehicles = config_manager.get_enabled_vehicles()
            
            # Създаване на custom ORToolsSolver
            custom_solver = SimplifiedORToolsSolver(
                test_config, enabled_vehicles, customers, distance_matrix, only_capacity
            )
            
            solution = custom_solver.solve()
            
            if solution and solution.is_feasible and len(solution.routes) > 0:
                print(f"   ✅ Намерено решение: {len(solution.routes)} маршрута")
                print(f"   📏 Разстояние: {solution.total_distance_km:.1f} км")
                return True
            else:
                print(f"   ❌ Не е намерено решение")
                return False
                
        finally:
            osrm_client.close()
            
    except Exception as e:
        print(f"   ❌ Грешка: {e}")
        return False

class SimplifiedORToolsSolver(ORToolsSolver):
    """Опростен OR-Tools solver за диагностика"""
    
    def __init__(self, config, vehicle_configs, customers, distance_matrix, only_capacity=False):
        super().__init__(config, vehicle_configs, customers, distance_matrix)
        self.only_capacity = only_capacity
    
    def solve(self):
        """Опростено решение само с capacity или без time constraints"""
        try:
            from ortools.constraint_solver import routing_enums_pb2
            from ortools.constraint_solver import pywrapcp
            
            # Създаване на модела
            manager = pywrapcp.RoutingIndexManager(
                len(self.distance_matrix.locations),
                self._get_total_vehicles(),
                self.depot
            )
            routing = pywrapcp.RoutingModel(manager)
            
            # Distance callback
            distance_callback_index = routing.RegisterTransitCallback(
                self._distance_callback_wrapper(manager)
            )
            routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)
            
            # Добавяне САМО на capacity ограничения
            self._add_capacity_constraints(routing, manager)
            
            # БЕЗ time constraints ако е тест
            if not self.only_capacity:
                self._add_time_constraints(routing, manager, distance_callback_index)
            
            # По-агресивни параметри за търсене
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = getattr(
                routing_enums_pb2.FirstSolutionStrategy, 
                self.config.first_solution_strategy
            )
            search_parameters.local_search_metaheuristic = getattr(
                routing_enums_pb2.LocalSearchMetaheuristic,
                self.config.local_search_metaheuristic
            )
            search_parameters.time_limit.seconds = self.config.time_limit_seconds
            search_parameters.log_search = self.config.log_search
            
            # Решаване
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                return self._extract_solution(manager, routing, solution)
            else:
                return None
                
        except Exception as e:
            print(f"   Грешка в SimplifiedORToolsSolver: {e}")
            return None

if __name__ == "__main__":
    test_ortools_minimal() 