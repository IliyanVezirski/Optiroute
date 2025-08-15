# 🚛 CVRP Optimizer - Напреднал Оптимизатор за Маршрути

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![OR-Tools](https://img.shields.io/badge/OR--Tools-9.7+-green.svg)](https://developers.google.com/optimization)
[![OSRM](https://img.shields.io/badge/OSRM-5.27+-orange.svg)](https://github.com/Project-OSRM/osrm-backend)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**CVRP Optimizer** е професионална софтуерна система за решаване на **Capacitated Vehicle Routing Problem (CVRP)** с интеграция на реални географски данни, математическа оптимизация и интелигентни бизнес правила. Системата използва **Google OR-Tools** за оптимизация и **OSRM** за реални разстояния и времена.

---

## 📋 Съдържание

- [🏗️ Архитектура на системата](#️-архитектура-на-системата)
- [⚡ Ключови функционалности](#-ключови-функционалности)
- [🚀 Технологичен стек](#-технологичен-стек)
- [🔧 Инсталация и настройка](#-инсталация-и-настройка)
- [📊 Подробен анализ на модулите](#-подробен-анализ-на-модулите)
- [🔬 Алгоритми и стратегии](#-алгоритми-и-стратегии)
- [🗺️ Интерактивна визуализация](#️-интерактивна-визуализация)
- [⚙️ Конфигурационна система](#️-конфигурационна-система)
- [🏁 Стартиране и използване](#-стартиране-и-използване)
- [📈 Performance и мащабиране](#-performance-и-мащабиране)
- [🔍 Troubleshooting](#-troubleshooting)

---

## 🏗️ Архитектура на системата

CVRP Optimizer е изграден като модулна система с ясно разделение на отговорностите:

```
┌─────────────────────────────────────────────────────────────┐
│                    CVRP OPTIMIZER                           │
├─────────────────────────────────────────────────────────────┤
│                     main.py                                 │
│                 (Оркестратор)                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐    ┌──────────────┐
│ INPUT   │    │   SOLVER    │    │   OUTPUT     │
│ LAYER   │    │   LAYER     │    │   LAYER      │
└─────────┘    └─────────────┘    └──────────────┘
    │               │                    │
    ▼               ▼                    ▼
┌─────────┐    ┌─────────────┐    ┌──────────────┐
│ input_  │    │ cvrp_       │    │ output_      │
│ handler │    │ solver      │    │ handler      │
└─────────┘    └─────────────┘    └──────────────┘
    │               │                    │
┌─────────┐    ┌─────────────┐    ┌──────────────┐
│ GPS     │    │ warehouse_  │    │ Interactive  │
│ Parser  │    │ manager     │    │ Map          │
└─────────┘    └─────────────┘    └──────────────┘
    │               │                    │
┌─────────┐    ┌─────────────┐    ┌──────────────┐
│ Data    │    │ osrm_       │    │ Excel        │
│ Validation   │ client      │    │ Reports      │
└─────────┘    └─────────────┘    └──────────────┘
```

### Централизирана конфигурационна система

```python
# config.py - Централен конфигурационен файл
MainConfig
├── vehicles: List[VehicleConfig]     # Превозни средства
├── locations: LocationConfig         # GPS локации
├── osrm: OSRMConfig                 # OSRM интеграция
├── warehouse: WarehouseConfig       # Складова логика
├── cvrp: CVRPConfig                 # OR-Tools настройки
├── input: InputConfig               # Входни данни
├── output: OutputConfig             # Изходни файлове
├── logging: LoggingConfig           # Логиране
├── cache: CacheConfig               # Кеширане
└── performance: PerformanceConfig   # Performance настройки
```

---

## ⚡ Ключови функционалности

### 🚛 Интелигентно управление на флота

**Поддържани типове превозни средства:**
- **INTERNAL_BUS**: 7 бр. × 385 стекове, 8 мин. service time
- **CENTER_BUS**: 1 бр. × 270 стекове, 10 мин. service time  
- **EXTERNAL_BUS**: 3 бр. × 385 стекове, 7 мин. service time (изключени)
- **SPECIAL_BUS**: 2 бр. × 300 стекове, 6 мин. service time (изключени)
- **VRATZA_BUS**: 1 бр. × 360 стекове, 7 мин. service time (изключени)

**Advance vehicle constraints:**
```python
@dataclass
class VehicleConfig:
    vehicle_type: VehicleType
    capacity: int                                    # Капацитет в стекове
    count: int                                       # Брой превозни средства
    max_distance_km: Optional[int] = None           # Максимален пробег
    max_time_hours: int = 20                        # Максимално работно време
    service_time_minutes: int = 15                  # Време за обслужване
    enabled: bool = True                            # Активен/неактивен
    start_location: Optional[Tuple[float, float]]   # Начална точка (депо)
    max_customers_per_route: Optional[int] = None   # Максимален брой клиенти
    start_time_minutes: int = 480                   # Стартово време (8:00)
    tsp_depot_location: Optional[Tuple[float, float]] = None  # TSP депо
```

### 🎯 Център зона приоритизация

**Intelligent center zone logic:**
- **Радиус**: 1.8 км от центъра на града
- **CENTER_BUS приоритет**: 90% отстъпка за център зоната
- **Глоби за други автобуси**: 40,000 единици за влизане в центъра
- **Автоматично разпознаване**: GPS-базирано определяне на център зоната

```python
# Център зона логика
if customer_distance_to_center <= 1.8:  # км
    if vehicle_type == VehicleType.CENTER_BUS:
        cost = base_cost * 0.10  # 90% отстъпка
    else:
        cost = base_cost + 40000  # Глоба за влизане
```

### 🧠 TSP Оптимизация с Personalized Депа

**Vehicle-specific TSP optimization:**
- **INTERNAL_BUS**: TSP от главното депо (София)
- **CENTER_BUS**: TSP от главното депо (София)
- **EXTERNAL_BUS**: TSP от главното депо (София)
- **SPECIAL_BUS**: TSP от главното депо (София)
- **VRATZA_BUS**: TSP от Враца депо

```python
def _optimize_route_from_depot(self, customers, depot_location, vehicle_config):
    """
    OR-Tools TSP решател за оптимизация от персонализирано депо
    """
    # Използва vehicle_config.tsp_depot_location
    tsp_depot = vehicle_config.tsp_depot_location or vehicle_config.start_location
    
    # Създава TSP проблем с OR-Tools
    # Минимизира разстоянието без ограничения
    # Връща оптимизиран ред на клиентите
```

### 🏭 Интелигентна складова логика

**Двуетапна стратегия за разпределение:**

1. **Филтриране по размер:**
```python
if customer.volume > max_single_bus_capacity:
    warehouse_customers.append(customer)  # Твърде голям за всички бусове
elif customer.volume > config.max_bus_customer_volume:  # 120 стекове
    warehouse_customers.append(customer)  # Над лимита за обслужване
```

2. **Интелигентно сортиране:**
```python
sorted_customers = sorted(customers, key=lambda c: (
    c.volume,  # Първо по обем (малък → голям)
    -calculate_distance_km(c.coordinates, depot_location)  # После по разстояние (далечен → близо)
))
```

### ⚡ Паралелна обработка

**Multi-strategy concurrent solving:**

| Работник | First Solution Strategy | Local Search Metaheuristic |
|----------|-------------------------|----------------------------|
| 1 | GLOBAL_BEST_INSERTION | GUIDED_LOCAL_SEARCH |
| 2 | SAVINGS | GUIDED_LOCAL_SEARCH |
| 3 | GLOBAL_CHEAPEST_ARC | GUIDED_LOCAL_SEARCH |
| 4 | PATH_CHEAPEST_ARC | GUIDED_LOCAL_SEARCH |
| 5 | SAVINGS | SIMULATED_ANNEALING |
| 6 | PARALLEL_CHEAPEST_INSERTION | GUIDED_LOCAL_SEARCH |
| 7 | CHRISTOFIDES | GUIDED_LOCAL_SEARCH |

**Automatic winner selection:**
```python
# Избира най-доброто решение по fitness score (най-малко разстояние)
best_solution = min(valid_solutions, key=lambda s: s.fitness_score)
```

---

## 🚀 Технологичен стек

### Core Dependencies

```python
# Mathematical Optimization
ortools>=9.7.2996          # Google OR-Tools optimization suite
scipy>=1.9.0                # Scientific computing

# Data Processing & Analysis  
pandas>=1.5.0               # DataFrame operations
numpy>=1.21.0               # Numerical arrays
openpyxl>=3.0.9             # Excel file support

# Geospatial & Routing
requests>=2.28.0            # HTTP client for OSRM API
urllib3>=1.26.0             # Low-level HTTP library

# Visualization & UI
folium>=0.14.0              # Interactive maps with Leaflet.js

# User Experience
tqdm>=4.65.0                # Progress bars
```

### OR-Tools Integration

**Supported algorithms:**
- **Clarke-Wright Savings Algorithm**
- **Christofides Algorithm** 
- **Guided Local Search (GLS)**
- **Simulated Annealing**
- **Tabu Search**
- **Large Neighborhood Search (LNS)**

### OSRM Integration

**OSRM services utilized:**
- **Table Service**: Distance matrices за batch processing
- **Route Service**: Detailed routing geometries
- **Match Service**: GPS trace matching (planned)

---

## 🔧 Инсталация и настройка

### Системни изисквания

- **Python**: 3.8+ (тестван до 3.11)
- **Memory**: 2GB+ RAM (4GB+ за >200 клиента)
- **Storage**: 1GB за OSRM data и cache
- **Network**: Internet за OSRM fallback (опционално)

### Бърза инсталация

```bash
# 1. Клониране на репозиторията
git clone <repository-url>
cd cvrp-optimizer

# 2. Създаване на виртуална среда
python -m venv cvrp_env
source cvrp_env/bin/activate  # Linux/Mac
# cvrp_env\Scripts\activate   # Windows

# 3. Инсталиране на зависимости
pip install -r requirements.txt

# 4. Създаване на директории
mkdir -p data output/excel output/charts logs cache

# 5. Проверка на инсталацията
python -c "import ortools; print('OR-Tools:', ortools.__version__)"
```

### OSRM сървър (препоръчително)

**Docker setup за България:**
```bash
# 1. Download Bulgarian OSM data
wget https://download.geofabrik.de/europe/bulgaria-latest.osm.pbf

# 2. OSRM preprocessing
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/bulgaria-latest.osm.pbf
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-partition /data/bulgaria-latest.osrm
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-customize /data/bulgaria-latest.osrm

# 3. Start OSRM server
docker run -t -i -p 5000:5000 -v "${PWD}:/data" osrm/osrm-backend osrm-routed --algorithm mld /data/bulgaria-latest.osrm
```

---

## 📊 Подробен анализ на модулите

### 📥 input_handler.py - Входни данни

**Функционалности:**
- **Excel парсиране**: .xlsx, .xls файлове
- **GPS координати извличане**: Множество формати
- **Data validation**: Проверка на валидност
- **Duplicate detection**: Намиране на дублиращи се записи

```python
class GPSParser:
    @staticmethod
    def parse_gps_string(gps_string: str) -> Optional[Tuple[float, float]]:
        """
        Поддържани формати:
        - "42.123456, 23.567890"
        - "42.123456,23.567890" 
        - "42.123456 23.567890"
        - "N42.123456 E23.567890"
        """
```

**Data structures:**
```python
@dataclass
class Customer:
    id: str                                      # Уникален идентификатор
    name: str                                    # Име на клиента
    coordinates: Optional[Tuple[float, float]]   # GPS координати
    volume: float                                # Обем на заявката
    original_gps_data: str                       # Оригинални GPS данни
```

### 🏭 warehouse_manager.py - Складова логика

**Ключови функции:**
- **Capacity calculation**: Изчисляване на общ капацитет
- **Smart sorting**: Двумерно сортиране (обем + разстояние)
- **Center zone detection**: GPS-базирано разпознаване
- **Allocation optimization**: Оптимално разпределение

```python
def _sort_customers(self, customers: List[Customer]) -> List[Customer]:
    """
    Dual-criteria sorting:
    1. Volume (ascending): от малък към голям обем
    2. Distance (descending): от далечни към близо клиенти
    """
    return sorted(customers, key=lambda c: (
        c.volume,
        -calculate_distance_km(c.coordinates, self.location_config.depot_location)
    ))
```

**Advanced allocation strategy:**
```python
def _allocate_with_warehouse(self, sorted_customers, total_capacity):
    """
    Three-tier allocation:
    1. Size filtering: > max_single_bus_capacity → warehouse
    2. Policy filtering: > max_bus_customer_volume → warehouse  
    3. Capacity filling: Fill buses to 100% capacity
    """
```

### 🧠 cvrp_solver.py - Основен решаващ модул

**Архитектура на solver-а:**

```python
class ORToolsSolver:
    """
    OR-Tools CVRP решател с четири активни dimensions:
    - Capacity: Обемни ограничения
    - Distance: Разстоянни ограничения  
    - Stops: Ограничения за брой спирки
    - Time: Времеви ограничения
    """
    
    def solve(self) -> CVRPSolution:
        """
        Main solving pipeline:
        1. Create data model
        2. Setup routing model  
        3. Add constraints (4 dimensions)
        4. Apply center zone logic
        5. Solve with search parameters
        6. Extract and validate solution
        7. TSP optimization (optional)
        """
```

**Constraint implementation:**
```python
# 1. Capacity constraints
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index, 0, vehicle_capacities, True, "Capacity"
)

# 2. Distance constraints  
routing.AddDimensionWithVehicleCapacity(
    transit_callback_index, 0, vehicle_max_distances, True, "Distance"
)

# 3. Stop count constraints
routing.AddDimensionWithVehicleCapacity(
    stop_callback_index, 0, vehicle_max_stops, True, "Stops"
)

# 4. Time constraints (vehicle-specific service times)
routing.AddDimensionWithVehicleCapacity(
    time_callback_index, 0, vehicle_max_times, False, "Time"
)
```

### 🌐 osrm_client.py - OSRM интеграция

**Multi-tier fallback system:**
```python
def get_distance_matrix(self, locations):
    """
    Intelligent chunking strategy:
    - n ≤ 30: Direct Table API
    - 30 < n ≤ 500: Batch Table API с chunking  
    - n > 500: Parallel Route API calls
    """
    
    try:
        return self._local_osrm_request(locations)
    except OSRMLocalError:
        try:
            return self._public_osrm_request(locations)
        except OSRMPublicError:
            return self._haversine_approximation(locations)
```

**Advanced caching:**
```python
class OSRMCache:
    """
    Features:
    - MD5 hashing за cache keys
    - JSON serialization
    - TTL expiration (24h default)
    - Automatic cleanup на stale entries
    - Order-independent key generation
    """
```

### 📊 output_handler.py - Визуализация и отчети

**Интерактивна карта с реални маршрути:**
```python
def _get_osrm_route_geometry(self, waypoints):
    """
    OSRM Route API integration:
    - Real road-based routing geometry
    - Turn-by-turn navigation data
    - Fallback to straight lines
    """
    url = f"{osrm_url}/route/v1/driving/{coords_str}?geometries=geojson&overview=full"
    # Returns detailed route geometry for visualization
```

**Excel reporting:**
- **Detailed route analysis**
- **Vehicle utilization metrics**
- **Performance statistics**
- **Styled worksheets** със цветово кодиране

---

## 🔬 Алгоритми и стратегии

### Mathematical Formulation

CVRP Optimizer решава следната математическа формулация:

```
Minimize: Σ(i,j)∈A Σk∈K cij * xijk

Subject to:
- Σk∈K Σj∈V xijk = 1  ∀i ∈ C    (всеки клиент се посещава веднъж)
- Σi∈V xijk - Σi∈V xjik = 0  ∀j ∈ V, k ∈ K    (flow conservation)
- Σi∈C di * Σj∈V xijk ≤ Qk  ∀k ∈ K    (capacity constraint)
- Σi,j∈S xijk ≤ |S| - 1  ∀S ⊆ C, |S| ≥ 2    (subtour elimination)

Where:
- C = set of customers
- V = C ∪ {depots}
- K = set of vehicles  
- cij = cost (distance/time) от i до j
- di = demand на клиент i
- Qk = capacity на vehicle k
```

### Center Zone Priority Logic

```python
def apply_center_zone_logic(self, routing, manager):
    """
    Multi-callback system за center zone приоритизация:
    
    1. CENTER_BUS callback: 90% отстъпка в center zone
    2. EXTERNAL_BUS callback: 40,000 penalty в center zone  
    3. INTERNAL_BUS callback: 40,000 penalty в center zone
    4. SPECIAL_BUS callback: 40,000 penalty в center zone
    5. VRATZA_BUS callback: 40,000 penalty в center zone
    """
```

### TSP Post-optimization

```python
def _optimize_route_from_depot(self, customers, depot_location):
    """
    OR-Tools TSP решател за финална оптимизация:
    
    1. Create TSP problem (single vehicle, no constraints)
    2. Use Euclidean distance matrix
    3. Apply AUTOMATIC strategy за бързо решаване  
    4. Extract optimal customer sequence
    5. Recalculate accurate times със vehicle-specific service times
    """
```

---

## 🗺️ Интерактивна визуализация

### Advanced Folium Integration

**Features:**
- ✅ **Real OSRM route geometry** - истински пътища по улиците
- ✅ **Color-coded routes** - уникален цвят за всеки автобус
- ✅ **Interactive popups** - детайлна информация за маршрути
- ✅ **Distance/time statistics** - реални метрики от OSRM
- ✅ **Depot markers** - начални/крайни точки
- ✅ **Customer numbering** - ред на посещение
- ✅ **Warehouse visualization** - необслужени клиенти

**OSRM Route API integration:**
```python
def _get_osrm_route_geometry(self, start_coords, end_coords):
    """
    Real-time route geometry от OSRM Route API:
    
    GET /route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}
        ?geometries=geojson&overview=full&steps=false
        
    Returns: Detailed GeoJSON LineString geometry
    """
```

### Visual Features

**Map styling:**
- **Custom markers**: FontAwesome икони за различни типове
- **Route colors**: Unique colors за всеки автобус
- **Popup information**: Comprehensive route statistics
- **Layer control**: Toggle visibility на различни елементи

---

## ⚙️ Конфигурационна система

### Централизирана конфигурация

```python
# config.py структура
@dataclass
class MainConfig:
    vehicles: Optional[List[VehicleConfig]] = None
    locations: LocationConfig = field(default_factory=LocationConfig)
    osrm: OSRMConfig = field(default_factory=OSRMConfig)
    warehouse: WarehouseConfig = field(default_factory=WarehouseConfig)
    cvrp: CVRPConfig = field(default_factory=CVRPConfig)
    input: InputConfig = field(default_factory=InputConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
```

### Ключови настройки

**CVRP Solver настройки:**
```python
@dataclass
class CVRPConfig:
    algorithm: str = "or_tools"
    time_limit_seconds: int = 360
    first_solution_strategy: str = "CHRISTOFIDES"
    local_search_metaheuristic: str = "GUIDED_LOCAL_SEARCH"
    
    # Паралелна обработка
    enable_parallel_solving: bool = True
    num_workers: int = -1  # -1 = all cores minus one
    
    # Финална реконфигурация
    enable_final_depot_reconfiguration: bool = True
    
    # Пропускане на клиенти
    allow_customer_skipping: bool = True
    distance_penalty_disjunction: int = 45000
```

**Vehicle-specific настройки:**
```python
# Примерна конфигурация за INTERNAL_BUS
VehicleConfig(
    vehicle_type=VehicleType.INTERNAL_BUS,
    capacity=385,                    # стекове
    count=7,                         # брой автобуси
    max_distance_km=None,           # без лимит
    max_time_hours=20,              # максимално работно време
    service_time_minutes=8,         # време за обслужване
    enabled=True,                   # активен
    start_location=depot_center,    # стартова точка
    start_time_minutes=480,         # 8:00 AM
    tsp_depot_location=depot_main   # TSP от главното депо
)
```

---

## 🏁 Стартиране и използване

### Методи на стартиране

**1. EXE файл (препоръчително):**
```bash
# Автоматично търсене на input.xlsx
CVRP_Optimizer.exe

# С посочен файл
CVRP_Optimizer.exe data\custom_input.xlsx
CVRP_Optimizer.exe "C:\Path\To\File.xlsx"
```

**2. Python скрипт:**
```bash
python main.py                    # Търси data/input.xlsx
python main.py custom_file.xlsx   # Използва посочения файл
```

**3. Batch файл:**
```bash
start_cvrp.bat                   # Интерактивно стартиране
```

### Структура на входния файл

**Задължителни колони:**

| Колона | Описание | Пример |
|--------|----------|--------|
| Клиент | Уникален ID | "1001" |
| Име Клиент | Име на клиента | "Магазин Център" |
| GpsData | GPS координати | "42.123456, 23.567890" |
| Обем | Обем в стекове | 10.5 |

**Примерен входен файл:**
```
| Клиент | Име Клиент         | GpsData                | Обем |
|--------|-------------------|------------------------|------|
| 1001   | Магазин Център    | 42.697357, 23.323810  | 10.5 |
| 1002   | Офис Южен         | 42.684568, 23.319735  | 5.2  |
| 1003   | Склад Запад       | 42.693874, 23.301234  | 15.8 |
```

### Изходни файлове

**1. Интерактивна карта** - `output/interactive_map.html`:
- Real-time OSRM маршрути
- Color-coded автобуси  
- Interactive popups с детайли
- Distance/time статистики

**2. Excel отчет** - `output/excel/cvrp_report.xlsx`:
- Детайлни маршрути по автобуси
- Capacity utilization
- Performance метрики
- Customer sequence

**3. Лог файл** - `logs/cvrp.log`:
- Детайлна диагностика
- Performance статистики
- Error handling информация

---

## 📈 Performance и мащабиране

### Benchmark резултати

**Тестено на Intel i7-8700K, 16GB RAM, SSD:**

| Клиенти | First Solution | Good Solution | Best Solution | Memory |
|---------|---------------|---------------|---------------|--------|
| 25      | 5-15s         | 30-60s        | 2-5 min       | 150MB  |
| 50      | 15-30s        | 2-5 min       | 5-10 min      | 250MB  |
| 100     | 30-90s        | 5-10 min      | 10-20 min     | 400MB  |
| 200     | 90-180s       | 10-20 min     | 20-40 min     | 800MB  |
| 300     | 3-5 min       | 20-30 min     | 40-60 min     | 1.2GB  |

### OSRM Performance

- **Local server**: 100-500ms за 50×50 matrix
- **Public API**: 1-5s за същата matrix  
- **Cache hit ratio**: 85-95% при repeated runs

### Optimization strategies

**Memory optimization:**
```python
def optimize_for_large_datasets(self, num_customers):
    if num_customers > 500:
        # Enable sparse matrices
        self.use_sparse_matrices = True
        
        # Reduce cache size
        self.cache_size_limit = 50  # MB
        
        # Enable streaming processing
        self.enable_streaming = True
```

**Parallel processing:**
```python
def get_optimal_workers(self, num_customers):
    cores = os.cpu_count()
    
    if num_customers < 50:
        return 1  # Single-threaded за малки проблеми
    elif num_customers < 200:
        return max(2, cores // 2)  # Half cores
    else:
        return max(4, cores - 1)   # Most cores, leave 1 for OS
```

---

## 🔍 Troubleshooting

### Чести проблеми

**1. OR-Tools инсталация:**
```bash
# Windows: Visual C++ missing
# Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Memory error
pip install --no-cache-dir ortools

# Version conflicts  
pip install ortools==9.7.2996 --force-reinstall
```

**2. OSRM connectivity:**
```python
# Test OSRM connection
def test_osrm():
    import requests
    try:
        response = requests.get("http://localhost:5000/route/v1/driving/23.3,42.7;23.3,42.7", timeout=10)
        return response.status_code == 200
    except:
        return False
```

**3. Memory issues:**
```python
# Memory profiling
import tracemalloc
tracemalloc.start()

# Your code here

current, peak = tracemalloc.get_traced_memory()
print(f"Memory: {current/1024/1024:.1f}MB (peak: {peak/1024/1024:.1f}MB)")
```

**4. Excel формат проблеми:**
```python
def validate_excel(file_path):
    required_columns = ['Клиент', 'Име Клиент', 'GpsData', 'Обем']
    df = pd.read_excel(file_path)
    
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
        
    if not pd.api.types.is_numeric_dtype(df['Обем']):
        raise ValueError("'Обем' must be numeric")
```

### Debug режим

**Enabling detailed debugging:**
```python
# config.py
DEBUG_CONFIG = {
    "debug_mode": True,
    "logging": {"log_level": "DEBUG"},
    "cvrp": {"log_search": True},
    "osrm": {"enable_request_logging": True}
}
```

**Performance profiling:**
```bash
python -m cProfile -o profile.prof main.py data/input.xlsx
python -c "import pstats; p=pstats.Stats('profile.prof'); p.sort_stats('cumulative'); p.print_stats(10)"
```

---

## 🚀 Advanced Features

### JSON API (планирано)

```python
# REST API endpoint (planned)
@app.route('/api/v1/optimize', methods=['POST'])
def optimize_routes():
    """
    Accept JSON input:
    {
        "customers": [...],
        "vehicles": [...],
        "config": {...}
    }
    
    Return optimized routes as JSON
    """
```

### Real-time tracking (планирано)

```python
# GPS tracking integration
class RealTimeTracker:
    def track_vehicle_position(self, vehicle_id):
        """Track real-time vehicle positions"""
        
    def update_eta(self, route_id):
        """Update estimated arrival times"""
        
    def detect_delays(self):
        """Detect and report delivery delays"""
```

### Machine Learning optimization (планирано)

```python
# ML-based optimization
class MLOptimizer:
    def predict_traffic_patterns(self, timestamp, route):
        """Predict traffic based on historical data"""
        
    def optimize_departure_times(self, routes):
        """ML-optimized departure time scheduling"""
        
    def learn_from_actual_times(self, planned_vs_actual):
        """Improve predictions from actual delivery data"""
```

---

## 📚 Заключение

CVRP Optimizer е напреднала, professional-grade система за Vehicle Routing Problem optimization, която комбинира:

- **Математическа прецизност** с Google OR-Tools
- **Реални географски данни** с OSRM integration
- **Intelligent business logic** за център зона приоритизация
- **Advanced visualization** с интерактивни карти
- **Паралелна обработка** за оптимални резултати
- **Персонализирани TSP депа** за всеки тип автобус
- **Enterprise-ready архитектура** за мащабиране

Системата е готова за production използване и може да се адаптира за различни logistics и distribution сценарии.

---

## 📞 Support & Contributing

- **GitHub Issues**: За bug reports и feature requests
- **Documentation**: Detailed wiki в GitHub repository  
- **Contributing**: Pull requests са добре дошли
- **License**: MIT License

**Current Version**: 3.1.0  
**Last Update**: Януари 2025  
**Maintainer**: CVRP Optimizer Development Team
