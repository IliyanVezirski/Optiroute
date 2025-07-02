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
        
        # Изчисляваме обем
        route.total_volume = sum(c.volume for c in customers)
        
        # Изчисляваме разстояние и време
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
                 customers: List[Customer], distance_matrix: DistanceMatrix, unique_depots: List[Tuple[float, float]]):
        self.config = config
        self.vehicle_configs = vehicle_configs
        self.customers = customers
        self.distance_matrix = distance_matrix
        self.depot = 0  # депото е винаги индекс 0
        self.progress_tracker = ORToolsProgressTracker(
            time_limit_seconds=config.time_limit_seconds,
            num_customers=len(customers)
        )
        self.unique_depots = unique_depots
    
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
        """Решава CVRP с OR-Tools и multiple depots поддръжка"""
        if not ORTOOLS_AVAILABLE:
            logger.error("❌ OR-Tools не е инсталиран")
            return CVRPSolution([], 0, 0, 0, 0, False)
        
        try:
            # 1. Създаване на data model
            data = self._create_data_model()
            
            logger.info("📊 ВХОДНИ ДАННИ:")
            logger.info(f"   Customers: {len(self.customers)}")
            logger.info(f"   Total locations: {len(data['distance_matrix'])}")
            logger.info(f"   Vehicles: {data['num_vehicles']}")
            logger.info(f"   Депа: {len(self.unique_depots)}")
            
            # 2. Създаване на Index Manager с multiple starts/ends
            manager = pywrapcp.RoutingIndexManager(
                len(data['distance_matrix']),
                data['num_vehicles'],
                data['vehicle_starts'],  # Различни start депа
                data['vehicle_ends']     # Различни end депа
            )
            
            # 3. Създаване на Routing Model
            routing = pywrapcp.RoutingModel(manager)
            
            # 4. Distance callback
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return data['distance_matrix'][from_node][to_node]
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # 5. ПРИОРИТИЗАЦИЯ на центъра чрез fixed costs
            vehicle_types = data['vehicle_types']
            for vehicle_id, vehicle_type in enumerate(vehicle_types):
                if vehicle_type == VehicleType.CENTER_BUS:
                    routing.SetFixedCostOfVehicle(0, vehicle_id)  # най-евтин
                elif vehicle_type == VehicleType.INTERNAL_BUS:
                    routing.SetFixedCostOfVehicle(1000, vehicle_id)  # среден приоритет
                else:  # EXTERNAL_BUS
                    routing.SetFixedCostOfVehicle(2000, vehicle_id)  # най-скъп
            
            logger.info("✅ Задени приоритетни costs: Center=0, Internal=1000, External=2000")
            
            # 6. CAPACITY CONSTRAINT
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                return data['demands'][from_node]
            
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # null capacity slack
                data['vehicle_capacities'],  # vehicle maximum capacities
                True,  # start cumul to zero
                "Capacity",
            )
            
            # 7. DISTANCE CONSTRAINTS
            if any(d < 999999999 for d in data['vehicle_max_distances']):
                logger.info("✅ Distance constraints ВКЛЮЧЕНИ с 20% tolerance за OR-Tools")
                tolerant_limits = [int(d * 1.2) for d in data['vehicle_max_distances']]
                logger.info(f"   Original limits: {[d//1000 for d in data['vehicle_max_distances']]} км")
                logger.info(f"   Tolerant limits: {[d//1000 for d in tolerant_limits]} км")
                
                distance_dimension = routing.GetDimensionOrDie("Capacity")  # Използваме capacity dimension
                
                for vehicle_id in range(data['num_vehicles']):
                    if tolerant_limits[vehicle_id] < 999999999:
                        routing.AddVariableMaximizedByFinalizer(
                            distance_dimension.CumulVar(routing.Start(vehicle_id))
                        )
                        routing.AddVariableMaximizedByFinalizer(
                            distance_dimension.CumulVar(routing.End(vehicle_id))
                        )
            
            # 8. VEHICLE TYPE CONSTRAINTS
            self._add_vehicle_type_constraints(routing, manager, data)
            
            # 9. SEARCH PARAMETERS
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.SAVINGS
            search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            search_parameters.time_limit.seconds = self.config.time_limit_seconds
            search_parameters.log_search = False  # OR-Tools logging
            
            logger.info("🚀 Решавам CVRP модела с всички constraints...")
            
            # 10. SOLVE
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                logger.info("✅ OR-Tools намери решение!")
                return self._extract_solution(manager, routing, solution)
            else:
                status = routing.status()
                logger.error(f"❌ OR-Tools не намери решение! Статус: {status}")
                return self._create_backup_solution()
                
        except Exception as e:
            logger.error(f"❌ Грешка в OR-Tools solver: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_backup_solution()
    
    def _create_data_model(self):
        """Създава data model за OR-Tools с поддръжка за множество депа"""
        data = {}
        
        # Distance matrix остава същата - [депа] + [клиенти]
        data['distance_matrix'] = []
        for i in range(len(self.distance_matrix.distances)):
            row = []
            for j in range(len(self.distance_matrix.distances[i])):
                # Конвертираме в метри и integer (OR-Tools изисква integer)
                distance_meters = int(self.distance_matrix.distances[i][j])
                row.append(distance_meters)
            data['distance_matrix'].append(row)
        
        # Demands - депата имат demand 0, клиентите имат техните volumes
        num_depots = len(self.unique_depots)
        data['demands'] = [0] * num_depots  # Депата имат 0 demand
        for customer in self.customers:
            data['demands'].append(int(customer.volume * 100))  # в стотинки
        
        # Vehicle конфигурации
        data['vehicle_capacities'] = []
        data['vehicle_max_distances'] = []
        data['vehicle_types'] = []
        data['vehicle_starts'] = []  # Стартови депа за всеки автобус
        data['vehicle_ends'] = []    # Крайни депа за всеки автобус
        
        vehicle_idx = 0
        for vehicle_config in self.vehicle_configs:
            if vehicle_config.enabled:
                # Намираме кой depot index отговаря на start_location на този vehicle
                if vehicle_config.start_location:
                    depot_index = self.unique_depots.index(vehicle_config.start_location)
                else:
                    # Намираме основното депо (не center_location)
                    center_location = get_config().locations.center_location
                    main_depot = None
                    for depot in self.unique_depots:
                        if depot != center_location:
                            main_depot = depot
                            break
                    depot_index = self.unique_depots.index(main_depot) if main_depot else 0
                
                for _ in range(vehicle_config.count):
                    # Capacity в стотинки
                    capacity = int(vehicle_config.capacity * 100)
                    data['vehicle_capacities'].append(capacity)
                    
                    # Max distance в метри
                    max_dist = int(vehicle_config.max_distance_km * 1000) if vehicle_config.max_distance_km else 999999999
                    data['vehicle_max_distances'].append(max_dist)
                    
                    # Vehicle type за constraints
                    data['vehicle_types'].append(vehicle_config.vehicle_type)
                    
                    # Start/end депа за този автобус
                    data['vehicle_starts'].append(depot_index)
                    data['vehicle_ends'].append(depot_index)  # Връща се в същото депо
                    
                    logger.debug(f"   🚛 Vehicle {vehicle_idx} ({vehicle_config.vehicle_type.value}): "
                               f"depot_index={depot_index}, location={self.unique_depots[depot_index]}")
                    vehicle_idx += 1
        
        data['num_vehicles'] = len(data['vehicle_capacities'])
        
        logger.info(f"📋 MULTI-DEPOT DATA MODEL:")
        logger.info(f"   Брой депа: {len(self.unique_depots)}")
        logger.info(f"   Matrix size: {len(data['distance_matrix'])}x{len(data['distance_matrix'][0])}")
        logger.info(f"   Demands: {data['demands'][:min(10, len(data['demands']))]}... (първи 10)")
        logger.info(f"   Vehicle capacities: {data['vehicle_capacities']}")
        logger.info(f"   Vehicle starts: {data['vehicle_starts']}")
        logger.info(f"   Vehicle types: {[vt.value for vt in data['vehicle_types']]}")
        
        return data
    
    def _add_vehicle_type_constraints(self, routing, manager, data):
        """Добавя ограничения за типовете превозни средства според имената на клиентите"""
        logger.info("🚛 Добавям ограничения за типове превозни средства с приоритет на center bus...")
        
        vehicle_types = data['vehicle_types']
        
        # Броим типове клиенти
        center_count = sum(1 for c in self.customers if "Център" in c.name or "Center" in c.name.lower())
        external_count = sum(1 for c in self.customers if "Външен" in c.name or "External" in c.name.lower())
        internal_count = len(self.customers) - center_count - external_count
        
        logger.info(f"📊 Типове клиенти: Center={center_count}, External={external_count}, Internal={internal_count}")
        
        # Всички клиенти могат да се обслужват от всички автобуси, но с приоритет
        # Center Bus има най-висок приоритет (поставяме го първо в списъка)
        for customer_idx, customer in enumerate(self.customers):
            node_index = customer_idx + 1  # +1 защото depot е 0
            allowed_vehicles = []
            
            # ПРИОРИТИЗАЦИЯ: Center Bus > Internal Bus > External Bus
            # 1. Първо добавяме Center Bus автобусите
            for vehicle_id, vehicle_type in enumerate(vehicle_types):
                if vehicle_type == VehicleType.CENTER_BUS:
                    allowed_vehicles.append(vehicle_id)
            
            # 2. След това Internal Bus автобусите  
            for vehicle_id, vehicle_type in enumerate(vehicle_types):
                if vehicle_type == VehicleType.INTERNAL_BUS:
                    allowed_vehicles.append(vehicle_id)
            
            # 3. Накрая External Bus автобусите
            for vehicle_id, vehicle_type in enumerate(vehicle_types):
                if vehicle_type == VehicleType.EXTERNAL_BUS:
                    allowed_vehicles.append(vehicle_id)
            
            # Задаваме ограничението с приоритизирания списък
            routing.SetAllowedVehiclesForIndex(allowed_vehicles, manager.NodeToIndex(node_index))
            
            logger.debug(f"   Клиент '{customer.name}' -> Автобуси {allowed_vehicles} (center приоритет)")
        
        logger.info(f"✅ Добавени ограничения за {len(self.customers)} клиента с center bus приоритет")
    
    def _extract_solution(self, manager, routing, solution) -> CVRPSolution:
        """Извлича решението от OR-Tools с поддръжка за множество депа"""
        routes = []
        total_distance = 0
        total_time = 0
        
        num_vehicles = routing.vehicles()
        num_depots = len(self.unique_depots)
        
        for vehicle_id in range(routing.vehicles()):
            route_customers = []
            route_distance = 0
            route_time = 0
            
            # Определяме кое е депото за този vehicle според data model
            vehicle_config = self._get_vehicle_config_for_id(vehicle_id)
            
            # ВАЖНО: Специален случай за CENTER_BUS - винаги използва center_location
            if vehicle_config.vehicle_type.value == 'center_bus':
                from config import get_config
                depot_location = get_config().locations.center_location
                logger.info(f"🎯 Автобус {vehicle_id} е CENTER_BUS - използвам center_location: {depot_location}")
            elif vehicle_config.start_location:
                depot_index = self.unique_depots.index(vehicle_config.start_location)
                depot_location = self.unique_depots[depot_index]
            else:
                depot_index = 0  # Основното депо
                depot_location = self.unique_depots[depot_index]
            
            index = routing.Start(vehicle_id)
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                # Проверяваме дали това е клиент (не депо)
                if node_index >= num_depots:  # Клиентите са след депата в матрицата
                    # Customer index е node_index - брой депа
                    customer_index = node_index - num_depots
                    if 0 <= customer_index < len(self.customers):
                        customer = self.customers[customer_index]
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
                # Добавяме service time за всеки клиент (10 минути според config)
                total_service_time = len(route_customers) * vehicle_config.service_time_minutes * 60  # в секунди
                
                route = Route(
                    vehicle_type=vehicle_config.vehicle_type,
                    vehicle_id=vehicle_id,
                    customers=route_customers,
                    depot_location=depot_location,
                    total_distance_km=route_distance / 1000,  # от метри в км
                    total_time_minutes=(route_time + total_service_time) / 60,  # в минути
                    total_volume=sum(c.volume for c in route_customers),
                    is_feasible=True
                )
                
                # Валидация на distance constraint
                if (vehicle_config.max_distance_km and 
                    route.total_distance_km > vehicle_config.max_distance_km):
                    logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                  f"надвишава distance лимит: {route.total_distance_km:.1f}км > "
                                  f"{vehicle_config.max_distance_km}км")
                    route.is_feasible = False
                
                # Валидация на capacity constraint  
                if route.total_volume > vehicle_config.capacity:
                    logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                  f"надвишава capacity лимит: {route.total_volume:.1f}ст > "
                                  f"{vehicle_config.capacity}ст")
                    route.is_feasible = False
                
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
        
        # Проверка на общата валидност на решението
        invalid_routes = [r for r in routes if not r.is_feasible]
        if invalid_routes:
            cvrp_solution.is_feasible = False
            logger.error(f"❌ {len(invalid_routes)} от {len(routes)} маршрута нарушават ограниченията!")
            for route in invalid_routes:
                vehicle_config = self._get_vehicle_config_for_id(route.vehicle_id)
                logger.error(f"   Автобус {route.vehicle_id} ({vehicle_config.vehicle_type.value}): "
                           f"{route.total_distance_km:.1f}км/{vehicle_config.max_distance_km}км, "
                           f"{route.total_volume:.1f}ст/{vehicle_config.capacity}ст")
        else:
            logger.info("✅ Всички маршрути съответстват на ограниченията")
        
        # Финална информация в прогрес tracker-а  
        if hasattr(self, 'progress_tracker'):
            self.progress_tracker.best_solution_value = total_distance
            
        logger.info(f"OR-Tools намери решение с {len(routes)} маршрута")
        logger.info(f"Общо разстояние: {cvrp_solution.total_distance_km:.2f} км")
        logger.info(f"Решение е валидно: {'✅ Да' if cvrp_solution.is_feasible else '❌ Не'}")
        
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
    
    def _create_backup_solution(self) -> CVRPSolution:
        """Интелигентен fallback алгоритъм ако OR-Tools не работи - СПАЗВА КМ ОГРАНИЧЕНИЯ"""
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
                    
                # Запълваме автобуса според капацитета И километрите му
                route_customers = []
                current_volume = 0.0
                current_distance = 0.0
                remaining_customers = []
                
                for customer in current_customers:
                    # Проверка за capacity constraint
                    if current_volume + customer.volume > vehicle_config.capacity:
                        remaining_customers.append(customer)
                        continue
                    
                    # Изчисляваме разстоянието ако добавим този клиент
                    depot_idx = 0  # depot е винаги 0
                    customer_idx = self.customers.index(customer) + 1  # +1 защото depot е 0
                    
                    # Разстояние от депо до клиент
                    distance_to_customer = self.distance_matrix.distances[depot_idx][customer_idx] / 1000  # в км
                    # Разстояние от клиент обратно до депо
                    distance_back = self.distance_matrix.distances[customer_idx][depot_idx] / 1000  # в км
                    
                    # Общо разстояние за този клиент (round trip)
                    total_trip_distance = distance_to_customer + distance_back
                    
                    # Проверка за distance constraint
                    if (vehicle_config.max_distance_km and 
                        current_distance + total_trip_distance > vehicle_config.max_distance_km):
                        remaining_customers.append(customer)
                        continue
                    
                    # Добавяме клиента ако отговаря на всички constraints
                    route_customers.append(customer)
                    current_volume += customer.volume
                    current_distance += total_trip_distance
                
                current_customers = remaining_customers
                
                if route_customers:
                    # Изчисляваме реалното разстояние за маршрута
                    route_distance_km = self._calculate_real_route_distance(route_customers)
                    route_time_minutes = self._calculate_real_route_time(route_customers)
                    
                    # Проверяваме дали маршрутът е валиден
                    is_feasible = True
                    if (vehicle_config.max_distance_km and 
                        route_distance_km > vehicle_config.max_distance_km):
                        is_feasible = False
                        logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                     f"надвишава km лимит: {route_distance_km:.1f}км > {vehicle_config.max_distance_km}км")
                    
                    if current_volume > vehicle_config.capacity:
                        is_feasible = False
                        logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                     f"надвишава capacity лимит: {current_volume:.1f}ст > {vehicle_config.capacity}ст")
                    
                    route = Route(
                        vehicle_type=vehicle_config.vehicle_type,
                        vehicle_id=vehicle_id,
                        customers=route_customers,
                        depot_location=self.distance_matrix.locations[0],
                        total_volume=current_volume,
                        total_distance_km=route_distance_km,
                        total_time_minutes=route_time_minutes,
                        is_feasible=is_feasible
                    )
                    routes.append(route)
                    
                    status_icon = "✅" if is_feasible else "❌"
                    logger.info(f"{status_icon} Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}): "
                              f"{len(route_customers)} клиента, {current_volume:.1f}/{vehicle_config.capacity}ст, "
                              f"{route_distance_km:.1f}/{vehicle_config.max_distance_km or 999}км")
                    vehicle_id += 1
        
        # Ако са останали клиенти, предупреждаваме
        if current_customers:
            logger.warning(f"⚠️ Останаха {len(current_customers)} клиента без разпределение - "
                         f"общ обем {sum(c.volume for c in current_customers):.1f} ст.")
            for customer in current_customers:
                logger.warning(f"   - {customer.name}: {customer.volume}ст")
        
        # Проверяваме общата валидност
        invalid_routes = [r for r in routes if not r.is_feasible]
        overall_feasible = len(invalid_routes) == 0 and len(current_customers) == 0
        
        if not overall_feasible:
            logger.error(f"❌ Решението НЕ е напълно валидно:")
            logger.error(f"   - Невалидни маршрути: {len(invalid_routes)}")
            logger.error(f"   - Неразпределени клиенти: {len(current_customers)}")
        else:
            logger.info("✅ Fallback решението е ВАЛИДНО и спазва всички ограничения!")
        
        return CVRPSolution(
            routes=routes,
            total_distance_km=sum(r.total_distance_km for r in routes),
            total_time_minutes=sum(r.total_time_minutes for r in routes),
            total_vehicles_used=len(routes),
            fitness_score=sum(r.total_distance_km for r in routes),
            is_feasible=overall_feasible
        )
    
    def _calculate_real_route_distance(self, route_customers: List[Customer]) -> float:
        """Изчислява реалното разстояние за маршрут спрямо OSRM матрицата"""
        if not route_customers:
            return 0.0
        
        total_distance = 0.0
        depot_idx = 0
        
        # От депо до първия клиент
        first_customer_idx = self.customers.index(route_customers[0]) + 1
        total_distance += self.distance_matrix.distances[depot_idx][first_customer_idx]
        
        # Между клиентите
        for i in range(len(route_customers) - 1):
            from_customer_idx = self.customers.index(route_customers[i]) + 1
            to_customer_idx = self.customers.index(route_customers[i + 1]) + 1
            total_distance += self.distance_matrix.distances[from_customer_idx][to_customer_idx]
        
        # От последния клиент обратно до депо
        last_customer_idx = self.customers.index(route_customers[-1]) + 1
        total_distance += self.distance_matrix.distances[last_customer_idx][depot_idx]
        
        return total_distance / 1000  # от метри в километри
    
    def _calculate_real_route_time(self, route_customers: List[Customer]) -> float:
        """Изчислява реалното време за маршрут спрямо OSRM матрицата"""
        if not route_customers:
            return 0.0
        
        total_time = 0.0
        depot_idx = 0
        
        # От депо до първия клиент
        first_customer_idx = self.customers.index(route_customers[0]) + 1
        total_time += self.distance_matrix.durations[depot_idx][first_customer_idx]
        
        # Между клиентите
        for i in range(len(route_customers) - 1):
            from_customer_idx = self.customers.index(route_customers[i]) + 1
            to_customer_idx = self.customers.index(route_customers[i + 1]) + 1
            total_time += self.distance_matrix.durations[from_customer_idx][to_customer_idx]
        
        # От последния клиент обратно до депо
        last_customer_idx = self.customers.index(route_customers[-1]) + 1
        total_time += self.distance_matrix.durations[last_customer_idx][depot_idx]
        
        # Добавяме service time (15 минути на клиент)
        service_time = len(route_customers) * 15 * 60  # в секунди
        
        return (total_time + service_time) / 60  # от секунди в минути


class CVRPSolver:
    """Главен клас за решаване на CVRP"""
    
    def __init__(self, config: Optional[CVRPConfig] = None):
        self.config = config or get_config().cvrp
        self.osrm_client = OSRMClient()
    
    def solve(self, allocation: WarehouseAllocation, depot_location: Tuple[float, float]) -> CVRPSolution:
        """Решава CVRP за дадените клиенти с поддръжка за множество депа"""
        logger.info("Започвам решаване на CVRP проблема")
        
        customers = allocation.vehicle_customers
        if not customers:
            logger.warning("Няма клиенти за оптимизация")
            return CVRPSolution([], 0, 0, 0, 0, True)

        # Получаване на включените превозни средства
        from config import config_manager
        enabled_vehicles = config_manager.get_enabled_vehicles()
        
        # СТЪПКА 1: Събираме всички уникални депа/start_location-и
        unique_depots = set()
        unique_depots.add(depot_location)  # Основното депо винаги се включва
        
        for vehicle_config in enabled_vehicles:
            if vehicle_config.start_location:
                unique_depots.add(vehicle_config.start_location)
        
        unique_depots = list(unique_depots)
        
        # ВАЖНО: Сортираме депата за консистентност - center депо първо
        # Това осигурява че center_location винаги ще е на индекс 0
        center_location = get_config().locations.center_location
        if center_location in unique_depots:
            unique_depots.remove(center_location)
            unique_depots.insert(0, center_location)  # Center депо на индекс 0
        
        logger.info(f"🏭 Уникални депа: {len(unique_depots)}")
        for i, depot in enumerate(unique_depots):
            if depot == center_location:
                logger.info(f"   Депо {i}: {depot} (CENTER)")
            elif depot == depot_location:
                logger.info(f"   Депо {i}: {depot} (MAIN)")
            else:
                logger.info(f"   Депо {i}: {depot}")
        
        # СТЪПКА 2: Създаваме разширена матрица: [депа] + [клиенти]
        all_locations = unique_depots + [c.coordinates for c in customers]
        
        logger.info("🔍 Търся матрица с разстояния в централния кеш...")
        distance_matrix = get_distance_matrix_from_central_cache(all_locations)
        
        if distance_matrix is None:
            logger.info("💾 Няма данни в кеша - правя нова OSRM заявка")
            distance_matrix = self.osrm_client.get_distance_matrix(all_locations)
        else:
            logger.info("✅ Използвам матрица от централния кеш - без OSRM заявки!")
        
        # Решаване с OR-Tools
        if self.config.algorithm == "or_tools":
            solver = ORToolsSolver(self.config, enabled_vehicles, customers, distance_matrix, unique_depots)
        else:
            logger.warning(f"Неподдържан алгоритъм: {self.config.algorithm}, използвам OR-Tools")
            solver = ORToolsSolver(self.config, enabled_vehicles, customers, distance_matrix, unique_depots)
        
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