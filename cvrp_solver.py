"""
CVRP Solver - основен модул за решаване на Vehicle Routing Problem
Използва OR-Tools за ефективна оптимизация
"""

import random
import math
import time
import threading
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
import logging
from tqdm import tqdm

# OR-Tools импорти
try:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logging.warning("OR-Tools не е инсталиран. Ще се използва опростен алгоритъм.")

from config import get_config, CVRPConfig, VehicleConfig, VehicleType
from input_handler import Customer
from osrm_client import DistanceMatrix, OSRMClient, get_distance_matrix_from_central_cache
from warehouse_manager import WarehouseAllocation

logger = logging.getLogger(__name__)


class ORToolsProgressTracker:
    """Клас за следене на прогреса на OR-Tools оптимизация"""
    
    def __init__(self, time_limit_seconds: int, num_customers: int):
        self.time_limit_seconds = time_limit_seconds
        self.num_customers = num_customers
        self.start_time = None
        self.best_solution_value = float('inf')
        self.solution_count = 0
        self.progress_bar = None
        self.running = False
        self.progress_thread = None
        
    def start_tracking(self):
        """Стартира следенето на прогреса"""
        self.start_time = time.time()
        self.running = True
        self.solution_count = 0
        
        # Създаваме прогрес бар
        self.progress_bar = tqdm(
            total=self.time_limit_seconds,
            desc=f"🔄 OR-Tools оптимизация ({self.num_customers} клиента)",
            unit="s",
            bar_format="{l_bar}{bar}| {n:.0f}/{total:.0f}s [{elapsed}<{remaining}, {postfix}]",
            dynamic_ncols=True
        )
        
        # Стартираме thread за обновяване на прогреса
        self.progress_thread = threading.Thread(target=self._update_progress)
        self.progress_thread.daemon = True
        self.progress_thread.start()
        
    def update_solution(self, solution_value: float):
        """Обновява най-доброто решение"""
        if solution_value < self.best_solution_value:
            self.best_solution_value = solution_value
            self.solution_count += 1
            
            # Обновяваме postfix информацията
            if self.progress_bar:
                improvement_percent = ((self.best_solution_value / self.best_solution_value * 100) 
                                     if self.best_solution_value > 0 else 0)
                self.progress_bar.set_postfix({
                    'решения': self.solution_count,
                    'най-добро': f'{self.best_solution_value/1000:.1f}км'
                })
    
    def _update_progress(self):
        """Обновява прогрес бара в отделен thread"""
        while self.running and self.progress_bar:
            if self.start_time:
                elapsed = time.time() - self.start_time
                if elapsed <= self.time_limit_seconds:
                    self.progress_bar.n = min(elapsed, self.time_limit_seconds)
                    self.progress_bar.refresh()
                else:
                    self.progress_bar.n = self.time_limit_seconds
                    self.progress_bar.refresh()
                    break
            time.sleep(0.5)  # Обновяваме на всеки 0.5 секунди
    
    def stop_tracking(self):
        """Спира следенето на прогреса"""
        self.running = False
        if self.progress_bar:
            # Довършваме прогрес бара
            elapsed = time.time() - self.start_time if self.start_time else 0
            self.progress_bar.n = min(elapsed, self.time_limit_seconds)
            
            # Финално съобщение
            final_msg = f"✅ Завършено - {self.solution_count} решения за {elapsed:.1f}s"
            if self.best_solution_value != float('inf'):
                final_msg += f" | Най-добро: {self.best_solution_value/1000:.1f}км"
            
            self.progress_bar.set_description(final_msg)
            self.progress_bar.refresh()
            self.progress_bar.close()
            
        if self.progress_thread and self.progress_thread.is_alive():
            self.progress_thread.join(timeout=1.0)


@dataclass
class Route:
    """Представлява маршрут за едно превозно средство"""
    vehicle_type: VehicleType
    vehicle_id: int
    customers: List[Customer]
    depot_location: Tuple[float, float]
    total_distance_km: float = 0.0
    total_time_minutes: float = 0.0
    total_volume: float = 0.0
    is_feasible: bool = True


@dataclass
class CVRPSolution:
    """Цялостно решение на CVRP проблема"""
    routes: List[Route]
    total_distance_km: float
    total_time_minutes: float
    total_vehicles_used: int
    fitness_score: float
    is_feasible: bool


class RouteBuilder:
    """Клас за построяване и валидация на маршрути"""
    
    def __init__(self, vehicle_configs: List[VehicleConfig], distance_matrix: DistanceMatrix):
        self.vehicle_configs = vehicle_configs
        self.distance_matrix = distance_matrix
        self.locations = distance_matrix.locations  # [depot, customer1, customer2, ...]
    
    def build_route(self, vehicle_type: VehicleType, vehicle_id: int, 
                   customer_indices: List[int], depot_location: Tuple[float, float]) -> Route:
        """Построява маршрут за дадено превозно средство"""
        vehicle_config = self._get_vehicle_config(vehicle_type)
        customers = [self._get_customer_by_index(idx) for idx in customer_indices]
        
        route = Route(
            vehicle_type=vehicle_type,
            vehicle_id=vehicle_id,
            customers=customers,
            depot_location=depot_location
        )
        
        # Изчисляване на обем
        route.total_volume = sum(c.volume for c in customers)
        
        # Изчисляване на разстояние и време
        if customer_indices:
            route.total_distance_km, route.total_time_minutes = self._calculate_route_metrics(customer_indices)
        
        # Валидация
        route.is_feasible = self._validate_route(route, vehicle_config)
        
        return route
    
    def _get_vehicle_config(self, vehicle_type: VehicleType) -> VehicleConfig:
        """Намира конфигурацията за дадения тип превозно средство"""
        for config in self.vehicle_configs:
            if config.vehicle_type == vehicle_type:
                return config
        raise ValueError(f"Няма конфигурация за превозно средство от тип {vehicle_type}")
    
    def _get_customer_by_index(self, index: int) -> Customer:
        """Връща клиент по индекс в матрицата (индекс 0 е депото)"""
        # Това предполага че имаме достъп до оригиналните клиенти
        # В реалната имплементация трябва да предаваме списъка с клиенти
        return Customer(
            id=f"customer_{index}",
            name=f"Customer {index}",
            coordinates=self.locations[index],
            volume=0.0,  # ще се попълни от действителните данни
            original_gps_data=""
        )
    
    def _calculate_route_metrics(self, customer_indices: List[int]) -> Tuple[float, float]:
        """Изчислява общото разстояние и време за маршрута"""
        if not customer_indices:
            return 0.0, 0.0
        
        total_distance = 0.0
        total_time = 0.0
        
        # От депо до първия клиент
        current_index = 0  # депо
        for next_index in customer_indices:
            distance = self.distance_matrix.distances[current_index][next_index]
            duration = self.distance_matrix.durations[current_index][next_index]
            
            total_distance += distance
            total_time += duration
            current_index = next_index
        
        # От последния клиент обратно в депото
        distance = self.distance_matrix.distances[current_index][0]
        duration = self.distance_matrix.durations[current_index][0]
        total_distance += distance
        total_time += duration
        
        # Добавяне на времето за обслужване на клиентите
        service_time = len(customer_indices) * 15 * 60  # 15 минути в секунди за всеки клиент
        total_time += service_time
        
        return total_distance / 1000, total_time / 60  # в км и минути
    
    def _validate_route(self, route: Route, vehicle_config: VehicleConfig) -> bool:
        """Валидира дали маршрутът е допустим"""
        # Проверка на капацитета
        if route.total_volume > vehicle_config.capacity:
            return False
        
        # Проверка на времето
        if route.total_time_minutes > vehicle_config.max_time_hours * 60:
            return False
        
        # Проверка на разстоянието (ако има ограничение)
        if vehicle_config.max_distance_km and route.total_distance_km > vehicle_config.max_distance_km:
            return False
        
        return True


class ORToolsSolver:
    """OR-Tools CVRP решател"""
    
    def __init__(self, config: CVRPConfig, vehicle_configs: List[VehicleConfig], 
                 customers: List[Customer], distance_matrix: DistanceMatrix):
        self.config = config
        self.vehicle_configs = vehicle_configs
        self.customers = customers
        self.distance_matrix = distance_matrix
        self.depot = 0  # депото е винаги индекс 0
        self.progress_tracker = ORToolsProgressTracker(
            time_limit_seconds=config.time_limit_seconds,
            num_customers=len(customers)
        )
    
    def _get_angle_to_depot(self, lat, lon):
        """Изчислява ъгъла между точка и депото спрямо север"""
        depot_lat, depot_lon = self.distance_matrix.locations[0]
        dx = lon - depot_lon
        dy = lat - depot_lat
        angle = math.degrees(math.atan2(dx, dy))
        # Нормализираме до 0-360
        return (angle + 360) % 360
    
    def _are_points_in_same_sector(self, from_node, to_node):
        """Проверява дали две точки са в един и същ сектор спрямо депото"""
        if from_node == 0 or to_node == 0:  # ако една от точките е депо
            return True
            
        from_lat, from_lon = self.distance_matrix.locations[from_node]
        to_lat, to_lon = self.distance_matrix.locations[to_node]
        
        from_angle = self._get_angle_to_depot(from_lat, from_lon)
        to_angle = self._get_angle_to_depot(to_lat, to_lon)
        
        # Дефинираме сектори от по 45 градуса
        SECTOR_SIZE = 45
        from_sector = int(from_angle / SECTOR_SIZE)
        to_sector = int(to_angle / SECTOR_SIZE)
        
        # Точките са в един сектор или съседни сектори
        return abs(from_sector - to_sector) <= 1 or abs(from_sector - to_sector) == 7
    
    def _distance_callback_wrapper(self, manager):
        """Wrapper за distance callback функцията"""
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            
            base_distance = self.distance_matrix.distances[from_node][to_node]
            
            # Ако точките не са в един и същ или съседен сектор,
            # добавяме голяма penalty
            if not self._are_points_in_same_sector(from_node, to_node):
                # Увеличаваме разстоянието значително
                return int(base_distance * 3)
            
            # За точки в един и същ сектор, използваме реалното разстояние
            return int(base_distance)
        
    def solve(self) -> CVRPSolution:
        """Решава CVRP проблема с OR-Tools"""
        if not ORTOOLS_AVAILABLE:
            logger.error("❌ OR-Tools НЕ Е НАЛИЧЕН! Използвам backup алгоритъм")
            logger.error("   Инсталирайте OR-Tools с: pip install ortools")
            return self._fallback_solution()
        
        logger.info("✅ OR-Tools е наличен, започвам решаване на CVRP")
        
        try:
            # Създаване на модела
            manager = pywrapcp.RoutingIndexManager(
                len(self.distance_matrix.locations),
                self._get_total_vehicles(),
                self.depot
            )
            routing = pywrapcp.RoutingModel(manager)
            
            # Регистриране на callback за разстояния - опростен вариант
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(self.distance_matrix.distances[from_node][to_node])
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            
            # Задаваме разстоянието като cost function
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Добавяме capacity constraints - опростен вариант
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                if from_node == 0:  # депо
                    return 0
                customer = self.customers[from_node - 1]  # -1 защото депото е 0
                return int(customer.volume)
            
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            
            vehicle_capacities = []
            for vehicle_config in self.vehicle_configs:
                if vehicle_config.enabled:
                    for _ in range(vehicle_config.count):
                        vehicle_capacities.append(int(vehicle_config.capacity))
            
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # нулев slack
                vehicle_capacities,  # максимален капацитет за всяко превозно средство
                True,  # започваме от 0
                "Capacity"
            )
            
            # Подобрени параметри за търсене
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC
            )
            search_parameters.time_limit.seconds = 1
            
            # Решаване
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                result = self._extract_solution(manager, routing, solution)
                logger.info("✅ OR-Tools намери решение успешно!")
                return result
            else:
                logger.error("❌ OR-Tools НЕ НАМЕРИ РЕШЕНИЕ! Използвам backup алгоритъм")
                logger.error(f"   Проблем: {len(self.customers)} клиента, {self._get_total_vehicles()} автобуса")
                return self._fallback_solution()
                
        except Exception as e:
            logger.error(f"❌ ГРЕШКА В OR-TOOLS! Използвам backup алгоритъм")
            logger.error(f"   Exception: {type(e).__name__}: {e}")
            return self._fallback_solution()
    
    def _get_total_vehicles(self) -> int:
        """Изчислява общия брой превозни средства"""
        return sum(vehicle.count for vehicle in self.vehicle_configs if vehicle.enabled)
    
    def _extract_solution(self, manager, routing, solution) -> CVRPSolution:
        """Извлича решението от OR-Tools"""
        routes = []
        total_distance = 0
        total_time = 0
        
        for vehicle_id in range(routing.vehicles()):
            route_customers = []
            route_distance = 0
            route_time = 0
            
            index = routing.Start(vehicle_id)
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                if node_index != 0:  # не е депо
                    customer = self.customers[node_index - 1]  # -1 защото депото е 0
                    route_customers.append(customer)
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                # Вземаме действителните разстояния от матрицата
                from_node = manager.IndexToNode(previous_index)
                to_node = manager.IndexToNode(index)
                actual_distance = self.distance_matrix.distances[from_node][to_node]
                actual_time = self.distance_matrix.durations[from_node][to_node]
                
                route_distance += actual_distance
                route_time += actual_time
            
            if route_customers:  # само ако има клиенти в маршрута
                # Намиране на типа превозно средство за този vehicle_id
                vehicle_config = self._get_vehicle_config_for_id(vehicle_id)
                
                # Добавяме service time за всеки клиент (15 минути)
                total_service_time = len(route_customers) * 15 * 60  # в секунди
                
                route = Route(
                    vehicle_type=vehicle_config.vehicle_type,
                    vehicle_id=vehicle_id,
                    customers=route_customers,
                    depot_location=self.distance_matrix.locations[0],
                    total_distance_km=route_distance / 1000,  # от метри в км
                    total_time_minutes=(route_time + total_service_time) / 60,  # в минути
                    total_volume=sum(c.volume for c in route_customers),
                    is_feasible=True
                )
                routes.append(route)
                total_distance += route_distance
                total_time += route_time + total_service_time
        
        cvrp_solution = CVRPSolution(
            routes=routes,
            total_distance_km=total_distance / 1000,
            total_time_minutes=total_time / 60,
            total_vehicles_used=len(routes),
            fitness_score=total_distance / 1000,  # използваме разстоянието като fitness
            is_feasible=True
        )
        
        # Финална информация в прогрес tracker-а  
        if hasattr(self, 'progress_tracker'):
            self.progress_tracker.best_solution_value = total_distance
            
        logger.info(f"OR-Tools намери решение с {len(routes)} маршрута")
        logger.info(f"Общо разстояние: {cvrp_solution.total_distance_km:.2f} км")
        
        return cvrp_solution
    
    def _get_vehicle_config_for_id(self, vehicle_id: int) -> VehicleConfig:
        """Намира конфигурацията за превозно средство по ID"""
        current_id = 0
        for vehicle_config in self.vehicle_configs:
            if not vehicle_config.enabled:
                continue
            if current_id <= vehicle_id < current_id + vehicle_config.count:
                return vehicle_config
            current_id += vehicle_config.count
        
        # Fallback към първото включено превозно средство
        for vehicle_config in self.vehicle_configs:
            if vehicle_config.enabled:
                return vehicle_config
        
        raise ValueError("Няма включени превозни средства")
    
    def _fallback_solution(self) -> CVRPSolution:
        """Интелигентен fallback алгоритъм ако OR-Tools не работи"""
        logger.warning("🔄 ИЗПОЛЗВАМ BACKUP АЛГОРИТЪМ вместо OR-Tools")
        logger.warning("   Това НЕ е оптимално - проверете защо OR-Tools не работи!")
        
        routes = []
        current_customers = self.customers.copy()
        vehicle_id = 0
        
        # Сортираме клиентите по обем (малки първо за по-добро запълване)
        current_customers.sort(key=lambda c: c.volume)
        
        for vehicle_config in self.vehicle_configs:
            if not vehicle_config.enabled:
                continue
                
            for _ in range(vehicle_config.count):
                if not current_customers:
                    break
                    
                # Запълваме автобуса според капацитета му
                route_customers = []
                current_volume = 0.0
                remaining_customers = []
                
                for customer in current_customers:
                    if current_volume + customer.volume <= vehicle_config.capacity:
                        route_customers.append(customer)
                        current_volume += customer.volume
                    else:
                        remaining_customers.append(customer)
                
                current_customers = remaining_customers
                
                if route_customers:
                    route = Route(
                        vehicle_type=vehicle_config.vehicle_type,
                        vehicle_id=vehicle_id,
                        customers=route_customers,
                        depot_location=self.distance_matrix.locations[0],
                        total_volume=current_volume,
                        total_distance_km=100.0,  # приблизително
                        total_time_minutes=120.0,  # приблизително
                        is_feasible=True
                    )
                    routes.append(route)
                    logger.info(f"Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}): "
                              f"{len(route_customers)} клиента, {current_volume:.1f}/{vehicle_config.capacity} ст.")
                    vehicle_id += 1
        
        # Ако са останали клиенти, предупреждаваме
        if current_customers:
            logger.warning(f"Останаха {len(current_customers)} клиента без разпределение - "
                         f"общ обем {sum(c.volume for c in current_customers):.1f} ст.")
        
        return CVRPSolution(
            routes=routes,
            total_distance_km=sum(r.total_distance_km for r in routes),
            total_time_minutes=sum(r.total_time_minutes for r in routes),
            total_vehicles_used=len(routes),
            fitness_score=sum(r.total_distance_km for r in routes),
            is_feasible=True
        )


class CVRPSolver:
    """Главен клас за решаване на CVRP"""
    
    def __init__(self, config: Optional[CVRPConfig] = None):
        self.config = config or get_config().cvrp
        self.osrm_client = OSRMClient()
    
    def solve(self, allocation: WarehouseAllocation, depot_location: Tuple[float, float]) -> CVRPSolution:
        """Решава CVRP за дадените клиенти"""
        logger.info("Започвам решаване на CVRP проблема")
        
        customers = allocation.vehicle_customers
        if not customers:
            logger.warning("Няма клиенти за оптимизация")
            return CVRPSolution([], 0, 0, 0, 0, True)
        
        # Получаване на матрица с разстояния - ПЪРВО от централния кеш
        locations = [depot_location] + [c.coordinates for c in customers]
        
        logger.info("🔍 Търся матрица с разстояния в централния кеш...")
        distance_matrix = get_distance_matrix_from_central_cache(locations)
        
        if distance_matrix is None:
            logger.info("💾 Няма данни в кеша - правя нова OSRM заявка")
            distance_matrix = self.osrm_client.get_distance_matrix(locations)
        else:
            logger.info("✅ Използвам матрица от централния кеш - без OSRM заявки!")
        
        # Получаване на включените превозни средства
        from config import config_manager
        enabled_vehicles = config_manager.get_enabled_vehicles()
        
        # Решаване с OR-Tools
        if self.config.algorithm == "or_tools":
            solver = ORToolsSolver(self.config, enabled_vehicles, customers, distance_matrix)
        else:
            logger.warning(f"Неподдържан алгоритъм: {self.config.algorithm}, използвам OR-Tools")
            solver = ORToolsSolver(self.config, enabled_vehicles, customers, distance_matrix)
        
        solution = solver.solve()
        
        logger.info(f"CVRP решен: {solution.total_vehicles_used} превозни средства")
        
        return solution
    
    def close(self):
        """Затваря ресурсите"""
        self.osrm_client.close()


# Удобна функция
def solve_cvrp(allocation: WarehouseAllocation, depot_location: Tuple[float, float]) -> CVRPSolution:
    """Удобна функция за решаване на CVRP"""
    solver = CVRPSolver()
    try:
        return solver.solve(allocation, depot_location)
    finally:
        solver.close() 