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

from config import get_config, CVRPConfig, VehicleConfig, VehicleType, LocationConfig
from input_handler import Customer
from osrm_client import DistanceMatrix
from warehouse_manager import WarehouseAllocation

logger = logging.getLogger(__name__)

def calculate_distance_km(coord1: Optional[Tuple[float, float]], coord2: Tuple[float, float]) -> float:
    """Изчислява разстоянието между две GPS координати в километри"""
    if not coord1 or not coord2:
        return float('inf')
    
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return 6371 * c  # 6371 km е радиусът на Земята


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
    dropped_customers: List[Customer]
    total_distance_km: float
    total_time_minutes: float
    total_vehicles_used: int
    fitness_score: float # Основната стойност, която solver-ът минимизира (разстояние)
    is_feasible: bool
    total_served_volume: float = 0.0 # Обхът обслужен обем, използван за избор на "победител"


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
    """OR-Tools CVRP решател, опростена версия."""
    
    def __init__(self, config: CVRPConfig, vehicle_configs: List[VehicleConfig], 
                 customers: List[Customer], distance_matrix: DistanceMatrix, unique_depots: List[Tuple[float, float]], 
                 center_zone_customers: Optional[List[Customer]] = None, location_config: Optional[LocationConfig] = None):
        self.config = config
        self.vehicle_configs = vehicle_configs
        self.customers = customers
        self.distance_matrix = distance_matrix
        self.unique_depots = unique_depots
        self.center_zone_customers = center_zone_customers or []
        self.location_config = location_config

    def solve(self) -> CVRPSolution:
        """
        Решава CVRP проблема по класическия начин, като минимизира разстоянието
        и спазва 4-те твърди ограничения: обем, разстояние, брой клиенти и време.
        """
        if not ORTOOLS_AVAILABLE:
            logger.error("❌ OR-Tools не е инсталиран")
            return self._create_empty_solution()
        
        try:
            # 1. Създаване на data model и мениджър
            data = self._create_data_model()
            manager = pywrapcp.RoutingIndexManager(
                len(data['distance_matrix']), data['num_vehicles'], data['vehicle_starts'], data['vehicle_ends']
            )
            routing = pywrapcp.RoutingModel(manager)

            # 2. ЦЕНА НА МАРШРУТА = РАЗСТОЯНИЕ
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                # КРИТИЧЕН ФИКС: OR-Tools очаква ЦЯЛО ЧИСЛО.
                return int(self.distance_matrix.distances[from_node][to_node])
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

            # 3. ОГРАНИЧЕНИЯ (DIMENSIONS) - ВСИЧКИ СА АКТИВНИ
            # Обем
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                return int(data['demands'][from_node]) # int() за сигурност
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index, 0, data['vehicle_capacities'], True, "Capacity"
            )

            # Разстояние - АКТИВИРАНО
            routing.AddDimensionWithVehicleCapacity(
                transit_callback_index, 0, data['vehicle_max_distances'], True, "Distance"
            )

            # Брой клиенти (спирки) - АКТИВИРАНО
            def stop_callback(from_index):
                return 1 if manager.IndexToNode(from_index) not in data['depot_indices'] else 0
            stop_callback_index = routing.RegisterUnaryTransitCallback(stop_callback)
            routing.AddDimensionWithVehicleCapacity(
                stop_callback_index, 0, data['vehicle_max_stops'], True, "Stops"
            )

            # Време - АКТИВИРАНО
            def time_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                travel_time = self.distance_matrix.durations[from_node][to_node]
                service_time = data['service_times'][from_node]
                return int(service_time + travel_time) # КРИТИЧЕН ФИКС: Връщаме int
            
            time_callback_index = routing.RegisterTransitCallback(time_callback)
            routing.AddDimensionWithVehicleCapacity(
                time_callback_index, 0, data['vehicle_max_times'], False, "Time"
            )

            # 4. ЛОГИКА ЗА ПРОПУСКАНЕ НА КЛИЕНТИ - с ДИНАМИЧНА глоба по твоята формула
            logger.info("Използва се ДИНАМИЧНА глоба за пропускане на клиенти, базирана на разстояние и обем.")
            
            # Вземаме параметрите от конфигурацията
            distance_normalization_factor = self.config.distance_normalization_factor
            volume_normalization_factor = self.config.volume_normalization_factor
            distance_weight = self.config.distance_weight
            volume_weight = self.config.volume_weight
            max_discount_percentage = self.config.max_discount_percentage
            discount_factor_divisor = self.config.discount_factor_divisor
            distance_penalty_disjunction = self.config.distance_penalty_disjunction
            
            logger.info(f"Параметри от конфигурацията: distance_weight={distance_weight}, volume_weight={volume_weight}, "
                       f"max_discount={max_discount_percentage*100:.1f}%, discount_divisor={discount_factor_divisor}")

            # Създаваме списък с клиенти в център зоната за бързо търсене
            center_zone_customer_ids = {c.id for c in self.center_zone_customers}
            
            logger.info(f"🎯 Прилагане на приоритет за център зоната: {len(self.center_zone_customers)} клиента")

            # Глобален callback за намаляване на разходите за далечни клиенти с малък обем
            logger.info("🌟 Настройка на приоритети за далечни клиенти")
            
            # Вземаме параметрите от конфигурацията
            distance_normalization_factor = self.config.distance_normalization_factor
            volume_normalization_factor = self.config.volume_normalization_factor
            distance_weight = self.config.distance_weight
            volume_weight = self.config.volume_weight
            max_discount_percentage = self.config.max_discount_percentage
            discount_factor_divisor = self.config.discount_factor_divisor
            
            # Създаваме отделен callback за всеки тип превозно средство
            
            # 1. БАЗОВ CALLBACK - запазва оригиналните разходи
            def base_distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(self.distance_matrix.distances[from_node][to_node])
                
            base_callback_index = routing.RegisterTransitCallback(base_distance_callback)
            
            # Първо регистрираме базовия callback за всички превозни средства
            routing.SetArcCostEvaluatorOfAllVehicles(base_callback_index)
            
            # 2. CALLBACK за EXTERNAL_BUS и INTERNAL_BUS - намалява разходите за далечни клиенти с малък обем
            def priority_non_center_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                
                # Базова цена (разстояние)
                base_distance = self.distance_matrix.distances[from_node][to_node]
                
                # Ако това е клиент (не депо), прилагаме намаление според формулата
                if to_node >= len(self.unique_depots):
                    customer_index = to_node - len(self.unique_depots)
                    customer = self.customers[customer_index]
                    
                    # Данни за клиента
                    customer_volume = customer.volume
                    distance_from_depot_m = customer.distance_from_depot_m
                    
                    # Нормализиране на разстоянието - по-големите разстояния дават по-големи стойности
                    distance_factor = distance_from_depot_m / distance_normalization_factor
                    
                    # Нормализиране на обема - по-малките обеми дават по-големи стойности
                    volume_factor = (volume_normalization_factor - customer_volume) / volume_normalization_factor
                    
                    # Комбиниран фактор - колкото по-голям е, толкова по-голямо е намалението
                    combined_factor = (distance_factor * distance_weight) + (volume_factor * volume_weight)
                    
                    # Прилагаме намаление от 0% до max_discount_percentage на базовата цена
                    discount = min(max_discount_percentage, combined_factor / discount_factor_divisor)
                    
                    # Връщаме намалената цена
                    return int(base_distance * (1.0 - discount))
                
                # За всички други случаи връщаме оригиналната цена
                return int(base_distance)
            
            # Регистрираме callback-а за намаляване на разходите
            priority_non_center_callback_index = routing.RegisterTransitCallback(priority_non_center_callback)
            
            # Прилагаме callback-а САМО за EXTERNAL_BUS и INTERNAL_BUS превозни средства
            logger.info(f"🚛 Прилагане на приоритет за далечни клиенти само за EXTERNAL_BUS и INTERNAL_BUS")
            
            # Прилагаме callback-а за EXTERNAL_BUS превозни средства
            for vehicle_id in data['external_bus_vehicle_ids']:
                routing.SetArcCostEvaluatorOfVehicle(priority_non_center_callback_index, vehicle_id)
                logger.debug(f"  - Приложен приоритет за далечни клиенти за EXTERNAL_BUS #{vehicle_id}")
            
            # Прилагаме callback-а за INTERNAL_BUS превозни средства
            for vehicle_id in data['internal_bus_vehicle_ids']:
                routing.SetArcCostEvaluatorOfVehicle(priority_non_center_callback_index, vehicle_id)
                logger.debug(f"  - Приложен приоритет за далечни клиенти за INTERNAL_BUS #{vehicle_id}")
                
            # Прилагаме callback-а за SPECIAL_BUS превозни средства
            for vehicle_id in data['special_bus_vehicle_ids']:
                routing.SetArcCostEvaluatorOfVehicle(priority_non_center_callback_index, vehicle_id)
                logger.debug(f"  - Приложен приоритет за далечни клиенти за SPECIAL_BUS #{vehicle_id}")
                
            logger.info(f"✅ Настроен приоритет за далечни клиенти")
            
            # Все още добавяме възможност за пропускане на клиенти, но с по-ниско наказание
            for node_idx in range(len(self.unique_depots), len(data['distance_matrix'])):
                # Добавяме възможността за пропускане, но с умерена глоба
                routing.AddDisjunction([manager.NodeToIndex(node_idx)], distance_penalty_disjunction)

            # 5. ПРИОРИТИЗИРАНЕ НА CENTER_BUS ЗА ЦЕНТЪР ЗОНАТА
            if self.center_zone_customers and data['center_bus_vehicle_ids']:
                logger.info("🎯 Прилагане на приоритет за CENTER_BUS в център зоната")
                
                # Създаваме callback за приоритизиране на CENTER_BUS
                def center_bus_priority_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    # Ако това е клиент в център зоната
                    if to_node >= len(self.unique_depots):
                        customer_index = to_node - len(self.unique_depots)
                        customer = self.customers[customer_index]
                        
                        if customer.id in {c.id for c in self.center_zone_customers}:
                            # Намаляваме разходите за CENTER_BUS с 50%
                            return int(self.distance_matrix.distances[from_node][to_node] * 0.5)
                    
                    return int(self.distance_matrix.distances[from_node][to_node])
                
                # Регистрираме callback-а за CENTER_BUS превозните средства
                center_bus_callback_index = routing.RegisterTransitCallback(center_bus_priority_callback)
                
                for vehicle_id in data['center_bus_vehicle_ids']:
                    routing.SetArcCostEvaluatorOfVehicle(center_bus_callback_index, vehicle_id)
            
            # 6. ГЛОБА ЗА ОСТАНАЛИТЕ БУСОВЕ ЗА ВЛИЗАНЕ В ЦЕНТЪРА
            if data['external_bus_vehicle_ids'] and self.location_config and self.location_config.enable_center_zone_restrictions:
                logger.info("🚫 Прилагане на глоба за EXTERNAL_BUS в център зоната")
                
                # Създаваме callback за глоба на EXTERNAL_BUS
                def external_bus_penalty_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    # Ако това е клиент в център зоната
                    if to_node >= len(self.unique_depots):
                        customer_index = to_node - len(self.unique_depots)
                        customer = self.customers[customer_index]
                        
                        # Проверяваме дали клиентът е в център зоната
                        if customer.coordinates and self.location_config:
                            distance_to_center = calculate_distance_km(
                                customer.coordinates, 
                                self.location_config.center_location
                            )
                            if distance_to_center <= self.location_config.center_zone_radius_km:
                                # Увеличаваме разходите за EXTERNAL_BUS с конфигурируем множител
                                multiplier = self.location_config.external_bus_center_penalty_multiplier if self.location_config else 10.0
                                return int(self.distance_matrix.distances[from_node][to_node] * multiplier)
                    
                    return int(self.distance_matrix.distances[from_node][to_node])
                
                # Регистрираме callback-а за EXTERNAL_BUS превозните средства
                external_bus_callback_index = routing.RegisterTransitCallback(external_bus_penalty_callback)
                
                for vehicle_id in data['external_bus_vehicle_ids']:
                    routing.SetArcCostEvaluatorOfVehicle(external_bus_callback_index, vehicle_id)
            
            # 7. ГЛОБА ЗА INTERNAL_BUS ЗА ВЛИЗАНЕ В ЦЕНТЪРА
            if data['internal_bus_vehicle_ids'] and self.location_config and self.location_config.enable_center_zone_restrictions:
                logger.info("⚠️ Прилагане на глоба за INTERNAL_BUS в център зоната")
                
                # Създаваме callback за глоба на INTERNAL_BUS
                def internal_bus_penalty_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    # Ако това е клиент в център зоната
                    if to_node >= len(self.unique_depots):
                        customer_index = to_node - len(self.unique_depots)
                        customer = self.customers[customer_index]
                        
                        # Проверяваме дали клиентът е в център зоната
                        if customer.coordinates and self.location_config:
                            distance_to_center = calculate_distance_km(
                                customer.coordinates, 
                                self.location_config.center_location
                            )
                            if distance_to_center <= self.location_config.center_zone_radius_km:
                                # Увеличаваме разходите за INTERNAL_BUS с конфигурируем множител
                                multiplier = self.location_config.internal_bus_center_penalty_multiplier if self.location_config else 2.0
                                return int(self.distance_matrix.distances[from_node][to_node] * multiplier)
                    
                    return int(self.distance_matrix.distances[from_node][to_node])
                
                # Регистрираме callback-а за INTERNAL_BUS превозните средства
                internal_bus_callback_index = routing.RegisterTransitCallback(internal_bus_penalty_callback)
                
                for vehicle_id in data['internal_bus_vehicle_ids']:
                    routing.SetArcCostEvaluatorOfVehicle(internal_bus_callback_index, vehicle_id)
                    
            # 8. ГЛОБА ЗА SPECIAL_BUS ЗА ВЛИЗАНЕ В ЦЕНТЪРА
            if data['special_bus_vehicle_ids'] and self.location_config and self.location_config.enable_center_zone_restrictions:
                logger.info("🔶 Прилагане на глоба за SPECIAL_BUS в център зоната")
                
                # Създаваме callback за глоба на SPECIAL_BUS
                def special_bus_penalty_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    # Ако това е клиент в център зоната
                    if to_node >= len(self.unique_depots):
                        customer_index = to_node - len(self.unique_depots)
                        customer = self.customers[customer_index]
                        
                        # Проверяваме дали клиентът е в център зоната
                        if customer.coordinates and self.location_config:
                            distance_to_center = calculate_distance_km(
                                customer.coordinates, 
                                self.location_config.center_location
                            )
                            if distance_to_center <= self.location_config.center_zone_radius_km:
                                # Увеличаваме разходите за SPECIAL_BUS с конфигурируем множител
                                multiplier = self.location_config.special_bus_center_penalty_multiplier if self.location_config else 7.0
                                return int(self.distance_matrix.distances[from_node][to_node] * multiplier)
                    
                    return int(self.distance_matrix.distances[from_node][to_node])
                
                # Регистрираме callback-а за SPECIAL_BUS превозните средства
                special_bus_callback_index = routing.RegisterTransitCallback(special_bus_penalty_callback)
                
                for vehicle_id in data['special_bus_vehicle_ids']:
                    routing.SetArcCostEvaluatorOfVehicle(special_bus_callback_index, vehicle_id)
            
            # 9. ПАРАМЕТРИ НА ТЪРСЕНЕ (Стандартни)
            logger.info("Използват се стандартни параметри за търсене.")
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = self.config.time_limit_seconds
            search_parameters.log_search = self.config.log_search

            # 10. РЕШАВАНЕ
            logger.info(f"🚀 Стартирам решаване с пълни ограничения (времеви лимит: {self.config.time_limit_seconds}s)...")
            solution = routing.SolveWithParameters(search_parameters)
            
            # 11. ОБРАБОТКА НА РЕШЕНИЕТО
            if solution:
                return self._extract_solution(manager, routing, solution, data)
            else:
                logger.error("❌ OR-Tools не намери решение!")
                return self._create_empty_solution()
                
        except Exception as e:
            logger.error(f"❌ Грешка в OR-Tools solver: {e}", exc_info=True)
            return self._create_empty_solution()

    def _create_data_model(self):
        """
        Изцяло пренаписана функция, за да се гарантира, че ЧЕТИРИТЕ твърди ограничения
        (Обем, Разстояние, Брой клиенти, Време) се четат и прилагат СТРИКТНО
        от конфигурационния файл, без грешки или своеволия.
        """
        logger.info("--- СЪЗДАВАНЕ НА DATA MODEL (СТРИКТЕН РЕЖИМ) ---")
        data = {}
        data['distance_matrix'] = self.distance_matrix.distances
        data['demands'] = [0] * len(self.unique_depots) + [int(c.volume * 100) for c in self.customers]
        
        base_service_time = next((v.service_time_minutes for v in self.vehicle_configs if v.enabled), 15) * 60
        data['service_times'] = [0] * len(self.unique_depots) + [base_service_time] * len(self.customers)
        
        data['num_vehicles'] = sum(v.count for v in self.vehicle_configs if v.enabled)
        logger.info(f"  - Общо превозни средства: {data['num_vehicles']}")
        data['depot_indices'] = list(range(len(self.unique_depots)))

        vehicle_capacities = []
        vehicle_max_distances = []
        vehicle_max_stops = []
        vehicle_max_times = []
        vehicle_starts = []
        vehicle_ends = []
        
        logger.info("  - Зареждане на твърди ограничения от конфигурацията...")
        
        # Идентифицираме CENTER_BUS превозните средства
        center_bus_vehicle_ids = []
        external_bus_vehicle_ids = []
        internal_bus_vehicle_ids = []
        special_bus_vehicle_ids = []
        vehicle_id = 0
        
        logger.info("  - Настройка на депа за превозните средства:")
        
        for v_config in self.vehicle_configs:
            if v_config.enabled:
                depot_index = self._get_depot_index_for_vehicle(v_config)
                depot_location = self.unique_depots[depot_index]
                
                logger.info(f"    {v_config.vehicle_type.value}: депо {depot_index} ({depot_location})")
                
                for _ in range(v_config.count):
                    # Записваме ID-тата на CENTER_BUS превозните средства
                    if v_config.vehicle_type == VehicleType.CENTER_BUS:
                        center_bus_vehicle_ids.append(vehicle_id)
                    elif v_config.vehicle_type == VehicleType.EXTERNAL_BUS:
                        external_bus_vehicle_ids.append(vehicle_id)
                    elif v_config.vehicle_type == VehicleType.INTERNAL_BUS:
                        internal_bus_vehicle_ids.append(vehicle_id)
                    elif v_config.vehicle_type == VehicleType.SPECIAL_BUS:
                        special_bus_vehicle_ids.append(vehicle_id)
                    
                    # 1. Обем (Capacity) - стриктно
                    vehicle_capacities.append(int(v_config.capacity * 100))
                    
                    # 2. Разстояние (Distance) - стриктно
                    max_dist = int(v_config.max_distance_km * 1000) if v_config.max_distance_km else 999999999
                    vehicle_max_distances.append(max_dist)
                    
                    # 3. Брой клиенти (Stops) - стриктно
                    max_stops = v_config.max_customers_per_route if v_config.max_customers_per_route is not None else len(self.customers) + 1
                    vehicle_max_stops.append(max_stops)

                    # 4. Време (Time) - стриктно
                    vehicle_max_times.append(int(v_config.max_time_hours * 3600))
                    
                    vehicle_starts.append(depot_index)
                    vehicle_ends.append(depot_index)
                    vehicle_id += 1
        
        data['vehicle_capacities'] = vehicle_capacities
        data['vehicle_max_distances'] = vehicle_max_distances
        data['vehicle_max_stops'] = vehicle_max_stops
        data['vehicle_max_times'] = vehicle_max_times
        data['vehicle_starts'] = vehicle_starts
        data['vehicle_ends'] = vehicle_ends
        data['depot'] = 0 
        data['center_bus_vehicle_ids'] = center_bus_vehicle_ids
        data['external_bus_vehicle_ids'] = external_bus_vehicle_ids
        data['internal_bus_vehicle_ids'] = internal_bus_vehicle_ids
        data['special_bus_vehicle_ids'] = special_bus_vehicle_ids
        
        logger.info(f"  - Капацитети: {data['vehicle_capacities']}")
        logger.info(f"  - Макс. разстояния (м): {data['vehicle_max_distances']}")
        logger.info(f"  - Макс. спирки: {data['vehicle_max_stops']}")
        logger.info(f"  - Макс. времена (сек): {data['vehicle_max_times']}")
        logger.info(f"  - CENTER_BUS превозни средства: {center_bus_vehicle_ids}")
        logger.info(f"  - EXTERNAL_BUS превозни средства: {external_bus_vehicle_ids}")
        logger.info(f"  - INTERNAL_BUS превозни средства: {internal_bus_vehicle_ids}")
        logger.info(f"  - SPECIAL_BUS превозни средства: {special_bus_vehicle_ids}")
        logger.info("--- DATA MODEL СЪЗДАДЕН ---")
        return data

    def _get_depot_index_for_vehicle(self, vehicle_config: VehicleConfig) -> int:
        """Намира индекса на депото за дадено превозно средство."""
        if vehicle_config.start_location and vehicle_config.start_location in self.unique_depots:
            return self.unique_depots.index(vehicle_config.start_location)
        # Връщаме основното депо по подразбиране
        return 0

    def _extract_solution(self, manager, routing, solution, data) -> CVRPSolution:
        """Извлича решението от OR-Tools и го попълва в нашите структури."""
        logger.info("--- ИЗВЛИЧАНЕ НА РЕШЕНИЕ ---")
        start_time = time.time()
        
        # Директно взимаме "времевото измерение" от солвъра.
        # Това е "източникът на истината" за времето.
        time_dimension = routing.GetDimensionOrDie("Time")
        
        routes = []
        total_distance = 0
        total_time_seconds = 0
        
        num_depots = len(self.unique_depots)
        all_serviced_customer_indices = set()
        
        for vehicle_id in range(routing.vehicles()):
            route_customers = []
            route_distance = 0
            
            # Определяме кое е депото за този vehicle според data model
            vehicle_config = self._get_vehicle_config_for_id(vehicle_id)
            
            # Вземаме депото директно от решението на OR-Tools
            start_node = manager.IndexToNode(routing.Start(vehicle_id))
            
            if start_node >= num_depots:
                # Това не би трябвало да се случва, тъй като всички маршрути трябва да започват от депо.
                # Но за всеки случай, логваме и пропускаме този автобус.
                logger.error(f"❌ Грешка: Автобус {vehicle_id} започва от клиент (node {start_node}), а не от депо. Маршрутът се игнорира.")
                continue

            depot_location = self.unique_depots[start_node]
            
            logger.info(f"Extracting route for vehicle {vehicle_id}")

            index = routing.Start(vehicle_id)
            max_iterations = len(self.customers) + 10  # Максимум итерации: брой клиенти + малко запас
            iteration_count = 0

            while not routing.IsEnd(index):
                iteration_count += 1
                if iteration_count > max_iterations:
                    logger.error(f"❌ Безкраен цикъл открит при извличане на маршрут за vehicle {vehicle_id}. Прекратявам.")
                    break

                node_index = manager.IndexToNode(index)
                # Проверяваме дали това е клиент (не депо)
                if node_index >= num_depots:  # Клиентите са след депата в матрицата
                    # Customer index е node_index - брой депа
                    customer_index = node_index - num_depots
                    if 0 <= customer_index < len(self.customers):
                        customer = self.customers[customer_index]
                        route_customers.append(customer)
                        all_serviced_customer_indices.add(customer_index)
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                # Вземаме действителните разстояния от матрицата
                from_node = manager.IndexToNode(previous_index)
                to_node = manager.IndexToNode(index)
                actual_distance = self.distance_matrix.distances[from_node][to_node]
                
                route_distance += actual_distance
            
            if route_customers:
                # КЛЮЧОВА ПРОМЯНА: Взимаме времето директно от решението на солвъра.
                # Това гарантира 100% консистентност между оптимизация и отчет.
                route_end_index = routing.End(vehicle_id)
                route_time_seconds = solution.Value(time_dimension.CumulVar(route_end_index))

                route = Route(
                    vehicle_type=vehicle_config.vehicle_type,
                    vehicle_id=vehicle_id,
                    customers=route_customers,
                    depot_location=depot_location,
                    total_distance_km=route_distance / 1000,
                    total_time_minutes=route_time_seconds / 60, # Превръщаме от секунди в минути
                    total_volume=sum(c.volume for c in route_customers),
                    is_feasible=True
                )
                
                # Връщаме валидациите, за да сме сигурни, че решението спазва правилата
                if (vehicle_config.max_distance_km and 
                    route.total_distance_km > vehicle_config.max_distance_km):
                    logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                  f"надвишава distance лимит: {route.total_distance_km:.1f}км > "
                                  f"{vehicle_config.max_distance_km}км")
                    route.is_feasible = False
                
                if route.total_volume > vehicle_config.capacity:
                    logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                  f"надвишава capacity лимит: {route.total_volume:.1f}ст > "
                                  f"{vehicle_config.capacity}ст")
                    route.is_feasible = False

                if (vehicle_config.max_customers_per_route and
                    len(route.customers) > vehicle_config.max_customers_per_route):
                     logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                   f"надвишава лимита за клиенти: {len(route.customers)} > "
                                   f"{vehicle_config.max_customers_per_route}")
                     route.is_feasible = False

                if route.total_time_minutes > (vehicle_config.max_time_hours * 60) + 1: # +1 за закръгления
                    logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                  f"надвишава time лимит: {route.total_time_minutes:.1f}мин > "
                                  f"{vehicle_config.max_time_hours * 60}мин")
                    route.is_feasible = False
                
                routes.append(route)
                total_distance += route_distance
                total_time_seconds += route_time_seconds
        
        logger.info(f"  - Извличане на маршрути отне: {time.time() - start_time:.2f} сек.")
        
        # НОВА ФУНКЦИОНАЛНОСТ: Финален реконфигурация на маршрутите от депото
        if self.config.enable_final_depot_reconfiguration:
            logger.info("🔄 Прилагане на финална реконфигурация на маршрутите от депото...")
            routes = self._reconfigure_routes_from_depot(routes)
        else:
            logger.info("⏭️ Пропускане на финална реконфигурация (изключена в конфигурацията)")
        
        # Намираме пропуснатите клиенти
        start_dropped_time = time.time()
        all_customer_indices = set(range(len(self.customers)))
        dropped_customer_indices = all_customer_indices - all_serviced_customer_indices
        dropped_customers = [self.customers[i] for i in dropped_customer_indices]
        
        if dropped_customers:
            logger.warning(f"⚠️ OR-Tools пропусна {len(dropped_customers)} клиента, за да намери решение:")
            # Сортираме по обем за по-ясно представяне
            dropped_customers.sort(key=lambda c: c.volume, reverse=True)
            for cust in dropped_customers[:10]: # показваме първите 10
                logger.warning(f"   - Пропуснат: {cust.name} (обем: {cust.volume:.1f} ст.)")
            if len(dropped_customers) > 10:
                logger.warning(f"   - ... и още {len(dropped_customers) - 10}")
        
        logger.info(f"  - Обработка на пропуснати клиенти отне: {time.time() - start_dropped_time:.2f} сек.")

        total_served_volume = sum(r.total_volume for r in routes)

        cvrp_solution = CVRPSolution(
            routes=routes,
            dropped_customers=dropped_customers,
            total_distance_km=total_distance / 1000,
            total_time_minutes=total_time_seconds / 60,
            total_vehicles_used=len(routes),
            fitness_score=float(solution.ObjectiveValue()),
            is_feasible=True, # Ще се обнови по-долу
            total_served_volume=total_served_volume
        )
        
        # Проверка на общата валидност на решението
        invalid_routes = [r for r in routes if not r.is_feasible]
        is_solution_feasible = not invalid_routes and not dropped_customers
        cvrp_solution.is_feasible = is_solution_feasible
        
        logger.info(f"--- РЕШЕНИЕТО ИЗВЛЕЧЕНО ({time.time() - start_time:.2f} сек.) ---")
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
    
    def _create_empty_solution(self) -> CVRPSolution:
        """Създава празно решение в случай на грешка."""
        return CVRPSolution(routes=[], dropped_customers=[], total_distance_km=0,
                            total_time_minutes=0, total_vehicles_used=0,
                            fitness_score=float('inf'), is_feasible=False, total_served_volume=0)

    def _reconfigure_routes_from_depot(self, routes: List[Route]) -> List[Route]:
        """
        Реконфигурира всички маршрути да започват от депото.
        Това е финална стъпка след като OR-Tools намери решение.
        """
        logger.info("🔄 Реконфигуриране на маршрутите от депото...")
        
        # Взимаме главното депо (индекс 0)
        main_depot = self.unique_depots[0]
        
        reconfigured_routes = []
        
        for route in routes:
            if not route.customers:
                continue
                
            # НОВА ЛОГИКА: Преизчисляваме оптималния ред на клиентите от депото
            optimized_customers = self._optimize_route_from_depot(route.customers, main_depot)
            
            # Изчисляваме новите разстояния и времена от депото
            new_distance_km, new_time_minutes = self._calculate_route_from_depot(
                optimized_customers, main_depot
            )
            
            # Създаваме нов маршрут с депото като стартова точка и оптимизиран ред
            reconfigured_route = Route(
                vehicle_type=route.vehicle_type,
                vehicle_id=route.vehicle_id,
                customers=optimized_customers,  # ОПТИМИЗИРАН ред на клиентите
                depot_location=main_depot,  # ВИНАГИ депото
                total_distance_km=new_distance_km,
                total_time_minutes=new_time_minutes,
                total_volume=sum(c.volume for c in optimized_customers),
                is_feasible=True
            )
            
            # Валидираме новия маршрут
            vehicle_config = self._get_vehicle_config_for_id(route.vehicle_id)
            
            # Сравняваме оригиналните и новите стойности
            logger.info(f"📊 Сравнение за маршрут {route.vehicle_id} ({vehicle_config.vehicle_type.value}):")
            logger.info(f"  - Оригинално: {route.total_distance_km:.1f}км, {route.total_time_minutes:.1f}мин")
            logger.info(f"  - От депото: {new_distance_km:.1f}км, {new_time_minutes:.1f}мин")
            logger.info(f"  - Разлика: +{new_distance_km - route.total_distance_km:.1f}км, +{new_time_minutes - route.total_time_minutes:.1f}мин")
            
            if not self._validate_reconfigured_route(reconfigured_route, vehicle_config):
                logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} НЕ спазва ограниченията!")
                reconfigured_route.is_feasible = False
            else:
                logger.info(f"✅ Реконфигуриран маршрут {route.vehicle_id} спазва ограниченията")
            
            reconfigured_routes.append(reconfigured_route)
        
        logger.info(f"✅ Реконфигурирани {len(reconfigured_routes)} маршрута от депото")
        return reconfigured_routes
    
    def _optimize_route_from_depot(self, customers: List[Customer], depot_location: Tuple[float, float]) -> List[Customer]:
        """
        Оптимизира реда на клиентите, започвайки от депото.
        Използва greedy алгоритъм за намиране на най-близкия клиент.
        """
        if not customers:
            return []
        
        # Намираме индекса на депото в матрицата
        depot_index = 0  # Винаги индекс 0 е главното депо
        
        optimized_customers = []
        remaining_customers = customers.copy()
        current_node = depot_index
        
        while remaining_customers:
            # Намираме най-близкия клиент от текущия node
            min_distance = float('inf')
            closest_customer = None
            closest_index = -1
            
            for i, customer in enumerate(remaining_customers):
                # Намираме индекса на клиента в матрицата
                customer_index = len(self.unique_depots) + self.customers.index(customer)
                
                # Разстояние от текущия node до клиента
                distance = self.distance_matrix.distances[current_node][customer_index]
                
                if distance < min_distance:
                    min_distance = distance
                    closest_customer = customer
                    closest_index = i
            
            if closest_customer:
                optimized_customers.append(closest_customer)
                remaining_customers.pop(closest_index)
                
                # Обновяваме текущия node
                customer_index = len(self.unique_depots) + self.customers.index(closest_customer)
                current_node = customer_index
        
        logger.debug(f"  - Оптимизиран ред на клиентите: {[c.name for c in optimized_customers]}")
        return optimized_customers
    
    def _calculate_route_from_depot(self, customers: List[Customer], depot_location: Tuple[float, float]) -> Tuple[float, float]:
        """
        Изчислява разстояние и време за маршрут, започващ от депото.
        """
        if not customers:
            return 0.0, 0.0
        
        total_distance = 0.0
        total_time = 0.0
        
        # Намираме индекса на депото в матрицата
        depot_index = 0  # Винаги индекс 0 е главното депо
        
        # Взимаме service time от конфигурацията
        service_time_minutes = next((v.service_time_minutes for v in self.vehicle_configs if v.enabled), 15)
        service_time_seconds = service_time_minutes * 60
        
        # От депо до първия клиент
        current_node = depot_index
        for customer in customers:
            # Намираме индекса на клиента в матрицата
            customer_index = len(self.unique_depots) + self.customers.index(customer)
            
            # Разстояние и време от текущия node до клиента
            distance = self.distance_matrix.distances[current_node][customer_index]
            duration = self.distance_matrix.durations[current_node][customer_index]
            
            total_distance += distance
            total_time += duration
            
            # Време за обслужване на клиента (само за клиенти, не за депо)
            total_time += service_time_seconds
            
            current_node = customer_index
        
        # От последния клиент обратно в депото
        distance = self.distance_matrix.distances[current_node][depot_index]
        duration = self.distance_matrix.durations[current_node][depot_index]
        
        total_distance += distance
        total_time += duration
        
        logger.debug(f"  - Изчислено от депото: {total_distance/1000:.1f}км, {total_time/60:.1f}мин")
        return total_distance / 1000, total_time / 60  # в км и минути
    
    def _validate_reconfigured_route(self, route: Route, vehicle_config: VehicleConfig) -> bool:
        """
        Валидира реконфигуриран маршрут спрямо ограниченията.
        """
        logger.info(f"🔍 Валидация на реконфигуриран маршрут {route.vehicle_id} ({vehicle_config.vehicle_type.value}):")
        logger.info(f"  - Разстояние: {route.total_distance_km:.1f}км (лимит: {vehicle_config.max_distance_km}км)")
        logger.info(f"  - Време: {route.total_time_minutes:.1f}мин (лимит: {vehicle_config.max_time_hours * 60}мин)")
        logger.info(f"  - Обем: {route.total_volume:.1f}ст (лимит: {vehicle_config.capacity}ст)")
        logger.info(f"  - Клиенти: {len(route.customers)} (лимит: {vehicle_config.max_customers_per_route})")
        
        # Проверка на капацитета
        if route.total_volume > vehicle_config.capacity:
            logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} надвишава capacity лимит")
            return False
        
        # Проверка на времето
        if route.total_time_minutes > vehicle_config.max_time_hours * 60:
            logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} надвишава time лимит")
            return False
        
        # Проверка на разстоянието (ако има ограничение)
        if vehicle_config.max_distance_km and route.total_distance_km > vehicle_config.max_distance_km:
            logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} надвишава distance лимит")
            return False
        
        # Проверка на брой клиенти
        if (vehicle_config.max_customers_per_route and 
            len(route.customers) > vehicle_config.max_customers_per_route):
            logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} надвишава лимита за клиенти")
            return False
        
        logger.info(f"✅ Маршрут {route.vehicle_id} спазва всички ограничения")
        return True

    def solve_simple(self) -> CVRPSolution:
        """
        Опростено решение, което точно следва класическия OR-Tools пример.
        Само capacity constraints, без допълнителни ограничения.
        """
        if not ORTOOLS_AVAILABLE:
            logger.error("❌ OR-Tools не е инсталиран")
            return self._create_empty_solution()
        
        try:
            # 1. Създаване на data model (опростен)
            data = self._create_simple_data_model()
            
            # 2. Създаване на мениджър (single depot)
            manager = pywrapcp.RoutingIndexManager(
                len(data['distance_matrix']), 
                data['num_vehicles'], 
                data['depot']
            )
            routing = pywrapcp.RoutingModel(manager)

            # 3. Distance callback - точно като в примера
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return data['distance_matrix'][from_node][to_node]
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

            # 4. Demand callback - точно като в примера
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                return data['demands'][from_node]
            
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            
            # 5. Capacity constraints - точно като в примера
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # null capacity slack
                data['vehicle_capacities'],  # vehicle maximum capacities
                True,  # start cumul to zero
                "Capacity"
            )

            # 6. Search parameters - точно като в примера
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = self.config.time_limit_seconds
            search_parameters.log_search = self.config.log_search
            
            # Настройки за избягване на "зависване" в опростения solver
            search_parameters.solution_limit = 100  # Ограничаваме броя решения
            search_parameters.use_unfiltered_first_solution_strategy = True  # По-бързо първо решение
            
            # LNS настройки
            lns_seconds = self.config.lns_time_limit_seconds
            search_parameters.lns_time_limit.seconds = int(lns_seconds)
            search_parameters.lns_time_limit.nanos = int((lns_seconds % 1) * 1e9)

            # 7. Решаване с progress tracking
            logger.info("🔄 Стартиране на опростен OR-Tools solver...")
            
            # Създаваме progress tracker
            progress_tracker = ORToolsProgressTracker(self.config.time_limit_seconds, len(self.customers))
            
            # Стартираме tracking
            progress_tracker.start_tracking()
            
            try:
                solution = routing.SolveWithParameters(search_parameters)
                
                # Спираме tracking
                progress_tracker.stop_tracking()
                
                # 8. Обработка на решението
                if solution:
                    logger.info("✅ Намерено решение с опростена логика")
                    return self._extract_simple_solution(manager, routing, solution, data)
                else:
                    logger.error("❌ Опростеният solver не намери решение")
                    return self._create_empty_solution()
                    
            except Exception as solve_error:
                progress_tracker.stop_tracking()
                raise solve_error

        except Exception as e:
            logger.error(f"❌ Грешка в опростения solver: {e}", exc_info=True)
            return self._create_empty_solution()

    def _create_simple_data_model(self):
        """Създава опростен data model като в OR-Tools примера"""
        data = {}
        
        # Distance matrix - използваме OSRM данните
        data['distance_matrix'] = self.distance_matrix.distances
        
        # Demands - депо има 0, клиенти имат реални стойности
        data['demands'] = [0] + [int(c.volume * 100) for c in self.customers]
        
        # Vehicle capacities - всички превозни средства
        data['vehicle_capacities'] = []
        for v_config in self.vehicle_configs:
            if v_config.enabled:
                for _ in range(v_config.count):
                    data['vehicle_capacities'].append(int(v_config.capacity * 100))
        
        # Брой превозни средства
        data['num_vehicles'] = len(data['vehicle_capacities'])
        
        # Депо - винаги индекс 0
        data['depot'] = 0
        
        logger.info(f"📊 Опростен data model: {len(self.customers)} клиента, {data['num_vehicles']} превозни средства")
        
        return data

    def _extract_simple_solution(self, manager, routing, solution, data) -> CVRPSolution:
        """Извлича решението от опростения solver"""
        routes = []
        total_distance = 0
        
        all_serviced_customer_indices = set()
        
        for vehicle_id in range(data['num_vehicles']):
            if not routing.IsVehicleUsed(solution, vehicle_id):
                continue
                
            route_customers = []
            route_distance = 0
            
            # Намираме конфигурацията на превозното средство
            vehicle_config = self._get_vehicle_config_for_id(vehicle_id)
            
            index = routing.Start(vehicle_id)
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                
                # Ако не е депо (индекс 0), добавяме клиента
                if node_index != 0:
                    customer_index = node_index - 1  # -1 защото депо е индекс 0
                    if 0 <= customer_index < len(self.customers):
                        customer = self.customers[customer_index]
                        route_customers.append(customer)
                        all_serviced_customer_indices.add(customer_index)
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                # Изчисляваме разстоянието
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            
            if route_customers:
                # Изчисляваме реалното разстояние в километри
                route_distance_km = route_distance / 1000
                
                # Изчисляваме времето (пътуване + обслужване)
                route_time_minutes = (route_distance / 40000) * 60  # 40 км/ч средна скорост
                route_time_minutes += len(route_customers) * vehicle_config.service_time_minutes
                
                route = Route(
                    vehicle_type=vehicle_config.vehicle_type,
                    vehicle_id=vehicle_id,
                    customers=route_customers,
                    depot_location=self.unique_depots[0],  # Основното депо
                    total_distance_km=route_distance_km,
                    total_time_minutes=route_time_minutes,
                    total_volume=sum(c.volume for c in route_customers),
                    is_feasible=True
                )
                
                routes.append(route)
                total_distance += route_distance
        
        # Намираме пропуснатите клиенти
        all_customer_indices = set(range(len(self.customers)))
        dropped_customer_indices = all_customer_indices - all_serviced_customer_indices
        dropped_customers = [self.customers[i] for i in dropped_customer_indices]
        
        if dropped_customers:
            logger.warning(f"⚠️ Пропуснати клиенти: {len(dropped_customers)}")
        
        # НОВА ФУНКЦИОНАЛНОСТ: Финален реконфигурация на маршрутите от депото
        if self.config.enable_final_depot_reconfiguration:
            logger.info("🔄 Прилагане на финална реконфигурация на маршрутите от депото (опростен solver)...")
            routes = self._reconfigure_routes_from_depot(routes)
        else:
            logger.info("⏭️ Пропускане на финална реконфигурация (изключена в конфигурацията)")
        
        total_served_volume = sum(r.total_volume for r in routes)
        
        return CVRPSolution(
            routes=routes,
            dropped_customers=dropped_customers,
            total_distance_km=total_distance / 1000,
            total_time_minutes=sum(r.total_time_minutes for r in routes),
            total_vehicles_used=len(routes),
            fitness_score=float(solution.ObjectiveValue()),
            is_feasible=True,
            total_served_volume=total_served_volume
        )


class CVRPSolver:
    """Главен клас за решаване на CVRP - опростена версия."""
    
    def __init__(self, config: Optional[CVRPConfig] = None):
        self.config = config or get_config().cvrp
    
    def solve(self, 
              allocation: WarehouseAllocation, 
              depot_location: Tuple[float, float],
              distance_matrix: DistanceMatrix) -> CVRPSolution:
        
        enabled_vehicles = get_config().vehicles or []
        
        unique_depots = {depot_location}
        for vehicle_config in enabled_vehicles:
            if vehicle_config.enabled and vehicle_config.start_location:
                unique_depots.add(vehicle_config.start_location)
        
        solver = ORToolsSolver(
            self.config, enabled_vehicles, allocation.vehicle_customers, 
            distance_matrix, sorted(list(unique_depots)), allocation.center_zone_customers,
            get_config().locations
        )
        
        # Избираме кой solver да използваме
        if self.config.use_simple_solver:
            logger.info("🔧 Използване на опростен solver (само capacity constraints)")
            return solver.solve_simple()
        else:
            logger.info("🔧 Използване на пълен solver (всички constraints)")
            return solver.solve()
    
    def close(self):
        pass


# Удобна функция
def solve_cvrp(allocation: WarehouseAllocation, 
               depot_location: Tuple[float, float], 
               distance_matrix: DistanceMatrix) -> CVRPSolution:
    """Удобна функция за решаване на CVRP"""
    solver = CVRPSolver()
    # close() вече не е нужен, тъй като няма OSRM клиент
    return solver.solve(allocation, depot_location, distance_matrix) 