"""
Централен конфигурационен файл за CVRP програма с OSRM
Съдържа всички настройки за всички модули
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


class VehicleType(Enum):
    """Типове превозни средства"""
    INTERNAL_BUS = "internal_bus"
    CENTER_BUS = "center_bus" 
    EXTERNAL_BUS = "external_bus"
    DISABLED = "disabled"


@dataclass
class VehicleConfig:
    """Конфигурация за превозно средство"""
    vehicle_type: VehicleType
    capacity: int  # стотинки обем
    count: int  # брой
    max_distance_km: Optional[int] = None  # ограничение в км
    max_time_hours: int = 8  # максимални часове работа
    service_time_minutes: int = 15  # време на спирка в минути
    enabled: bool = True  # дали е включено
    start_location: Optional[Tuple[float, float]] = None  # специална стартова точка
    max_customers_per_route: Optional[int] = None  # максимален брой клиенти на маршрут (None = без ограничение)


@dataclass
class LocationConfig:
    """GPS координати за важни локации"""
    depot_location: Tuple[float, float] = (42.695785029219415, 23.23165887245312)  # Стартова точка
    center_location: Tuple[float, float] = (42.69773576871825, 23.321588606946342)  # Точка център


@dataclass
class OSRMConfig:
    """Конфигурации за OSRM заявки"""
    base_url: str = "http://localhost:5000"  # локален OSRM сървър
    profile: str = "driving"  # driving, walking, cycling
    chunk_size: int = 80  # увеличен размер за по-ефективно обработване
    timeout_seconds: int = 45  # по-дълъг timeout за големи заявки
    retry_attempts: int = 3
    retry_delay_seconds: int = 1
    average_speed_kmh: float = 40.0  # средна скорост за изчисления
    use_cache: bool = True
    cache_expiry_hours: int = 24
    
    # Локални OSRM настройки
    fallback_to_public: bool = True  # включено - използваме публичен сървър като fallback
    public_osrm_url: str = "http://router.project-osrm.org"  # backup URL
    
    # Настройки за ефективност
    max_locations_for_osrm: int = 50  # над този брой - директно приблизителни стойности
    enable_smart_chunking: bool = True  # интелигентно chunking за ефективност


@dataclass
class InputConfig:
    """Конфигурации за входни данни"""
    excel_file_path: str = "data/input.xlsx"
    gps_column: str = "GpsData"
    client_id_column: str = "Клиент"
    client_name_column: str = "Име клиент"
    volume_column: str = "Обем"
    sheet_name: Optional[str] = None  # ако е None, взема първия лист
    encoding: str = "utf-8"


@dataclass
class WarehouseConfig:
    """Конфигурации за склад"""
    enable_warehouse: bool = True  # Включваме warehouse за балансиране
    sort_by_volume: bool = True  # сортиране от малък към голям
    move_largest_to_warehouse: bool = True  # най-големите заявки в склада
    warehouse_capacity_multiplier: float = 1.2  # колко пъти може да надвишава складa
    large_request_threshold: float = 0.50 # процент за "голяма заявка" (напр. 0.8 = 80%)
    ortools_target_utilization: float = 0.7  # целева утилизация за OR-Tools (напр. 0.7 = 70%)
    ortools_safe_utilization: float = 0.75  # максимална безопасна утилизация (напр. 0.75 = 75%)


@dataclass
class CVRPConfig:
    """Конфигурации за CVRP алгоритъм"""
    algorithm: str = "or_tools"  # or_tools, genetic, simulated_annealing, ant_colony
    
    # OR-Tools настройки - оптимизирани за стабилност
    time_limit_seconds: int = 150
    first_solution_strategy: str = "PATH_MOST_CONSTRAINED_ARC"  
    local_search_metaheuristic: str = "TABU_SEARCH"  
    log_search: bool = True  # изключено за по-бързо изпълнение
    
    # Общи настройки
    max_iterations: int = 1000  # за други алгоритми
    parallel_processing: bool = True
    random_seed: Optional[int] = None
    
    # Deprecated генетичен алгоритъм настройки (запазени за съвместимост)
    population_size: int = 100
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    elite_size: int = 20
    improvement_threshold: int = 50


@dataclass
class OutputConfig:
    """Конфигурации за изходни данни"""
    # Карта
    enable_interactive_map: bool = True
    map_output_file: str = "output/interactive_map.html"
    map_zoom_level: int = 12
    show_route_colors: bool = True
    show_vehicle_info: bool = True
    
    # Excel файлове
    excel_output_dir: str = "output/excel"
    warehouse_excel_file: str = "warehouse_orders.xlsx"
    routes_excel_file: str = "vehicle_routes.xlsx"
    efficiency_excel_file: str = "efficiency_report.xlsx"
    
    # Чартове и анализи
    enable_charts: bool = True
    charts_output_dir: str = "output/charts"
    efficiency_chart_file: str = "efficiency_analysis.png"
    route_comparison_file: str = "route_comparison.png"
    volume_distribution_file: str = "volume_distribution.png"
    
    # Детайлна информация
    include_detailed_info: bool = True
    show_km_info: bool = True
    show_time_info: bool = True
    show_volume_info: bool = True


@dataclass
class LoggingConfig:
    """Конфигурации за логиране"""
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_file: str = "logs/cvrp.log"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_console_logging: bool = True
    enable_file_logging: bool = True
    max_log_size_mb: int = 10
    backup_count: int = 5


@dataclass
class CacheConfig:
    """Конфигурации за кеширане"""
    enable_cache: bool = True
    cache_dir: str = "cache"
    osrm_cache_file: str = "osrm_matrix_cache.json"
    routes_cache_file: str = "routes_cache.json"
    cache_expiry_hours: int = 24
    max_cache_size_mb: int = 100


@dataclass
class PerformanceConfig:
    """Конфигурации за производителност"""
    max_concurrent_requests: int = 10
    chunk_processing_delay: float = 0.1  # секунди между chunks
    memory_limit_mb: int = 1024
    enable_multiprocessing: bool = True
    max_workers: int = 4


@dataclass
class MainConfig:
    """Главна конфигурация която съдържа всички останали"""
    # Модулни конфигурации
    locations: LocationConfig = LocationConfig()
    vehicles: Optional[List[VehicleConfig]] = None
    osrm: OSRMConfig = OSRMConfig()
    input: InputConfig = InputConfig()
    warehouse: WarehouseConfig = WarehouseConfig()
    cvrp: CVRPConfig = CVRPConfig()
    output: OutputConfig = OutputConfig()
    logging: LoggingConfig = LoggingConfig()
    cache: CacheConfig = CacheConfig()
    performance: PerformanceConfig = PerformanceConfig()
    
    # Глобални настройки
    debug_mode: bool = False
    verbose: bool = True
    dry_run: bool = False  # тестово изпълнение без реални операции
    
    def __post_init__(self):
        """Инициализира default vehicle конфигурации"""
        if self.vehicles is None:
            self.vehicles = self._create_default_vehicles()
    
    def _create_default_vehicles(self) -> List[VehicleConfig]:
        """Създава default конфигурации за превозните средства"""
        return [
            # 1. Вътрешни бусове - 4 бр, 360 ст, 50км ограничение
            VehicleConfig(
                vehicle_type=VehicleType.INTERNAL_BUS,
                capacity=360,
                count=4,
                max_distance_km=50,
                max_time_hours=8,
                service_time_minutes=10,
                enabled=True,
                max_customers_per_route=None
            ),
            # 2. Център бус - 1 бр, 250 ст, стартира от център
            VehicleConfig(
                vehicle_type=VehicleType.CENTER_BUS,
                capacity=250,
                count=1,
                max_distance_km=40,
                max_time_hours=8,
                service_time_minutes=10,
                enabled=True,
                start_location=self.locations.center_location,
                max_customers_per_route=None
            ),
            # 3. Външни бусове - 3 бр, 360 ст, 150км ограничение
            VehicleConfig(
                vehicle_type=VehicleType.EXTERNAL_BUS,
                capacity=360,
                count=3,
                max_distance_km=200,
                max_time_hours=8,
                service_time_minutes=10,
                enabled=True,
                max_customers_per_route=None
            )
        ]


class ConfigManager:
    """Мениджър за зареждане и записване на конфигурации"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = MainConfig()
    
    def load_config(self, config_dict: Optional[Dict[str, Any]] = None) -> MainConfig:
        """Зарежда конфигурация от файл или речник"""
        if config_dict:
            self._update_config_from_dict(config_dict)
        elif os.path.exists(self.config_file):
            self._load_from_file()
        
        # Създаване на необходими директории
        self._create_directories()
        
        return self.config
    
    def _load_from_file(self) -> None:
        """Зарежда конфигурация от JSON файл"""
        import json
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self._update_config_from_dict(config_data)
        except Exception as e:
            print(f"Грешка при зареждане на конфигурация: {e}")
    
    def _update_config_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Обновява конфигурацията от речник"""
        for section, values in config_dict.items():
            if hasattr(self.config, section) and isinstance(values, dict):
                section_config = getattr(self.config, section)
                for key, value in values.items():
                    if hasattr(section_config, key):
                        setattr(section_config, key, value)
    
    def save_config(self, config: Optional[MainConfig] = None) -> None:
        """Записва конфигурацията във файл"""
        if config:
            self.config = config
        
        config_dict = self._config_to_dict()
        
        import json
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Преобразува конфигурацията в речник"""
        result = {}
        
        for attr_name in dir(self.config):
            if attr_name.startswith('_'):
                continue
                
            attr_value = getattr(self.config, attr_name)
            
            if hasattr(attr_value, '__dict__'):
                # Dataclass обект
                result[attr_name] = {
                    k: v for k, v in attr_value.__dict__.items() 
                    if not k.startswith('_')
                }
            elif isinstance(attr_value, list):
                # Списък с dataclass обекти
                result[attr_name] = [
                    {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
                    if hasattr(item, '__dict__') else item
                    for item in attr_value
                ]
            elif not callable(attr_value):
                result[attr_name] = attr_value
        
        return result
    
    def _create_directories(self) -> None:
        """Създава необходимите директории"""
        directories = [
            os.path.dirname(self.config.input.excel_file_path),
            self.config.output.excel_output_dir,
            self.config.output.charts_output_dir,
            os.path.dirname(self.config.output.map_output_file),
            os.path.dirname(self.config.logging.log_file),
            self.config.cache.cache_dir
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    def get_config(self) -> MainConfig:
        """Връща текущата конфигурация"""
        return self.config
    
    def get_enabled_vehicles(self) -> List[VehicleConfig]:
        """Връща само включените превозни средства"""
        if self.config.vehicles is None:
            return []
        return [v for v in self.config.vehicles if v.enabled]
    
    def get_total_vehicle_capacity(self) -> int:
        """Изчислява общия капацитет на всички включени превозни средства"""
        return sum(v.capacity * v.count for v in self.get_enabled_vehicles())
    
    def update_vehicle_status(self, vehicle_type: VehicleType, enabled: bool) -> None:
        """Включва/изключва определен тип превозно средство"""
        if self.config.vehicles is None:
            return
        for vehicle in self.config.vehicles:
            if vehicle.vehicle_type == vehicle_type:
                vehicle.enabled = enabled


# Глобална инстанция на конфигурацията
config_manager = ConfigManager()

# Функции за лесен достъп до конфигурациите
def get_config() -> MainConfig:
    """Връща главната конфигурация"""
    return config_manager.get_config()

def get_osrm_config() -> OSRMConfig:
    """Връща OSRM конфигурацията"""
    return config_manager.get_config().osrm

def get_vehicle_configs() -> List[VehicleConfig]:
    """Връща конфигурациите на превозните средства"""
    return config_manager.get_enabled_vehicles()

def get_locations() -> LocationConfig:
    """Връща GPS локациите"""
    return config_manager.get_config().locations 