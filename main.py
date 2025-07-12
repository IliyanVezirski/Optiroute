"""
Главен файл за CVRP програма - Оркестратор на процеси
Координира всички модули за решаване на Vehicle Routing Problem,
включително паралелна обработка с различни стратегии.
"""

import logging
import sys
import time
import os
import copy
from typing import Optional, List, Dict, Any, Tuple
from multiprocessing import Pool, cpu_count
from dataclasses import asdict

# Импортираме всички необходими модули
from ortools.constraint_solver import routing_enums_pb2
from config import get_config, MainConfig, CVRPConfig, LocationConfig
from input_handler import InputHandler, InputData
from warehouse_manager import WarehouseManager, WarehouseAllocation
from cvrp_solver import CVRPSolver, CVRPSolution
from output_handler import OutputHandler
from osrm_client import OSRMClient, DistanceMatrix, get_distance_matrix_from_central_cache


def setup_logging():
    """Настройва основното логиране за главния процес."""
    config = get_config()
    log_config = config.logging
    
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    formatter = logging.Formatter(log_config.log_format)
    
    logger = logging.getLogger()
    try:
        logger.setLevel(getattr(logging, log_config.log_level.upper()))
    except AttributeError:
        logger.setLevel(logging.INFO)
    
    if log_config.enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if log_config.enable_file_logging:
        os.makedirs(os.path.dirname(log_config.log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_config.log_file, 'a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def prepare_data(input_file: Optional[str]) -> Tuple[Optional[InputData], Optional[WarehouseAllocation]]:
    """
    Стъпка 1: Подготвя всички входни данни.
    """
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("СТЪПКА 1: ПОДГОТОВКА НА ДАННИ")
    logger.info("="*60)
    
    input_handler = InputHandler()
    warehouse_manager = WarehouseManager()

    try:
        input_data = input_handler.load_data(input_file)
        if not input_data or not input_data.customers:
            logger.error("Не са намерени валидни клиенти във входния файл.")
            return None, None
        
        logger.info(f"Заредени {len(input_data.customers)} клиенти с общ обем {input_data.total_volume:.2f} ст.")
        
        warehouse_allocation = warehouse_manager.allocate_customers(input_data)
        warehouse_allocation = warehouse_manager.optimize_allocation(warehouse_allocation)
        
        logger.info(f"Разпределение: {len(warehouse_allocation.vehicle_customers)} за бусове, "
                    f"{len(warehouse_allocation.warehouse_customers)} за склад.")
        logger.info(f"Използване на капацитета: {warehouse_allocation.capacity_utilization*100:.1f}%")

        return input_data, warehouse_allocation
    except Exception as e:
        logger.error(f"Фатална грешка при подготовка на данните: {e}", exc_info=True)
        return None, None


def get_distance_matrix(
    allocation: WarehouseAllocation, 
    location_config: LocationConfig
) -> Optional[DistanceMatrix]:
    """
    Изчислява или зарежда от кеша матрицата с разстояния САМО ВЕДНЪЖ.
    """
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("СТЪПКА 1.5: ИЗЧИСЛЯВАНЕ НА МАТРИЦА С РАЗСТОЯНИЯ")
    logger.info("="*60)

    customers = allocation.vehicle_customers
    if not customers:
        logger.warning("Няма клиенти за solver-а, пропускам изчисляването на матрица.")
        return None
        
    enabled_vehicles = get_config().vehicles or []
    unique_depots = {location_config.depot_location}
    for vehicle_config in enabled_vehicles:
        if vehicle_config.enabled and vehicle_config.start_location:
            unique_depots.add(vehicle_config.start_location)
            
    sorted_depots = sorted(list(unique_depots), key=lambda x: (x[0], x[1]))

    all_locations = sorted_depots + [c.coordinates for c in customers if c.coordinates]
    
    logger.info(f"Общо локации за матрица: {len(all_locations)} ({len(sorted_depots)} депа, {len(customers)} клиента)")
    
    distance_matrix = get_distance_matrix_from_central_cache(all_locations)
    
    if distance_matrix is None:
        logger.info("Няма данни в кеша - правя нова OSRM заявка...")
        osrm_client = OSRMClient()
        try:
            distance_matrix = osrm_client.get_distance_matrix(all_locations)
        finally:
            osrm_client.close()
    else:
        logger.info("Успешно заредена матрица от централния кеш.")
        
    return distance_matrix


def generate_solver_configs(base_cvrp_config: CVRPConfig, num_workers: int) -> List[CVRPConfig]:
    """
    Генерира списък с различни конфигурации за паралелно тестване.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Генерирам {num_workers} варианта на конфигурации за паралелно решаване...")
    
    configs = []
    
    first_solution_strategies = base_cvrp_config.parallel_first_solution_strategies
    local_search_metaheuristics = base_cvrp_config.parallel_local_search_metaheuristics

    # Генерираме двойки стратегии, докато не запълним работниците
    for strategy in first_solution_strategies:
        for metaheuristic in local_search_metaheuristics:
            if len(configs) >= num_workers:
                break
            
            new_config = copy.deepcopy(base_cvrp_config)
            new_config.first_solution_strategy = strategy
            new_config.local_search_metaheuristic = metaheuristic
            
            if new_config not in configs:
                configs.append(new_config)
        
        if len(configs) >= num_workers:
            break
    
    # Ако все още нямаме достатъчно, добавяме базовата конфигурация
    if len(configs) < num_workers:
        if base_cvrp_config not in configs:
            configs.append(base_cvrp_config)

    logger.info(f"Създадени {len(configs)} уникални конфигурации за тестване.")
    return configs


def solve_cvrp_worker(worker_args: Tuple[WarehouseAllocation, Dict, Dict, DistanceMatrix, int]) -> Optional[CVRPSolution]:
    """
    "Работникът" - функцията, която се изпълнява паралелно.
    """
    warehouse_allocation, cvrp_config_dict, location_config_dict, distance_matrix, worker_id = worker_args
    cvrp_config = CVRPConfig(**cvrp_config_dict)
    location_config = LocationConfig(**location_config_dict)

    solver = CVRPSolver(cvrp_config)
    
    print(f"[Работник {worker_id}]: СТАРТ. Стратегия: {cvrp_config.first_solution_strategy}, "
          f"Метаевристика: {cvrp_config.local_search_metaheuristic}")
          
    solution = solver.solve(warehouse_allocation, location_config.depot_location, distance_matrix)
    
    if solution and solution.routes:
        # Изчисляваме общия обем за това решение
        total_volume = sum(r.total_volume for r in solution.routes)
        print(f"[Работник {worker_id}]: ЗАВЪРШЕН. Обслужен обем: {total_volume:.2f}, "
              f"Маршрути: {len(solution.routes)}, Пропуснати: {len(solution.dropped_customers)}")
        return solution
    
    print(f"[Работник {worker_id}]: ЗАВЪРШЕН. Не е намерено валидно решение.")
    return None


def process_results(
    solution: CVRPSolution,
    input_data: InputData,
    warehouse_allocation: WarehouseAllocation,
    execution_time: float
):
    """
    Стъпка 3: Обработва финалното (най-доброто) решение.
    """
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("СТЪПКА 3: ОБРАБОТКА НА РЕЗУЛТАТИТЕ")
    logger.info("="*60)
    
    output_handler = OutputHandler()
    
    logger.info("Генериране на изходни файлове...")
    output_files = output_handler.generate_all_outputs(
                solution, warehouse_allocation, input_data.depot_location
            )
            
    _print_summary(input_data, warehouse_allocation, solution, output_files, execution_time)
    
    logger.info("="*60)
    logger.info("CVRP ОПТИМИЗАЦИЯ ЗАВЪРШЕНА УСПЕШНО")
    logger.info("="*60)


def _print_summary(input_data, warehouse_allocation, solution, output_files, execution_time):
    """Отпечатва финално резюме на изпълнението."""
    logger = logging.getLogger(__name__)
    logger.info("\n" + "="*50)
    logger.info("РЕЗЮМЕ НА ОПТИМИЗАЦИЯТА")
    logger.info("="*50)
    
    logger.info(f"Време за изпълнение: {execution_time:.2f} секунди")
    
    logger.info("\nCVRP РЕШЕНИЕ:")
    logger.info(f"  Използвани превозни средства: {solution.total_vehicles_used}")
    logger.info(f"  Общо разстояние: {solution.total_distance_km:.2f} км")
    logger.info(f"  Общо време: {solution.total_time_minutes:.1f} минути")
    logger.info(f"  Fitness оценка: {solution.fitness_score:.2f}")
    logger.info(f"  Пропуснати клиенти: {len(solution.dropped_customers)}")
    
    # Детайли по маршрути
    if solution.routes:
        logger.info("\nДЕТАЙЛИ ПО МАРШРУТИ:")
        for i, route in enumerate(solution.routes):
            vehicle_name = route.vehicle_type.value.replace('_', ' ').title()
            logger.info(f"  Маршрут {i+1} ({vehicle_name}):")
            logger.info(f"    Клиенти: {len(route.customers)}, Обем: {route.total_volume:.2f} ст., "
                        f"Разстояние: {route.total_distance_km:.2f} км, Време: {route.total_time_minutes:.1f} мин")
    
    # Изходни файлове
    logger.info("\nГЕНЕРИРАНИ ФАЙЛОВЕ:")
    for file_type, file_path in output_files.items():
        file_type_name = file_type.replace('_', ' ').title()
        logger.info(f"  {file_type_name}: {file_path}")
    
    logger.info("="*50)


def main():
    """Главна функция - оркестратор."""
    start_time = time.time()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    config = get_config()

    input_file = sys.argv[1] if len(sys.argv) > 1 else None

    input_data, warehouse_allocation = prepare_data(input_file)
    if not input_data or not warehouse_allocation:
        sys.exit(1)

    # --- Стъпка 1.5: Изчисляване на матрица с разстояния ---
    distance_matrix = get_distance_matrix(warehouse_allocation, config.locations)
    if not distance_matrix:
        logger.error("Не може да се изчисли матрица с разстояния. Прекратявам работа.")
        sys.exit(1)

    logger.info("="*60)
    logger.info("СТЪПКА 2: РЕШАВАНЕ НА CVRP ПРОБЛЕМА")
    logger.info("="*60)

    best_solution = None

    cpu_cores = os.cpu_count() or 1
    if config.cvrp.enable_parallel_solving and cpu_cores > 1:
        if config.cvrp.num_workers == -1:
            num_workers = max(1, cpu_cores - 1)
        else:
            num_workers = config.cvrp.num_workers
        
        logger.info(f"🚀 Старирам паралелна обработка с {num_workers} работника...")
        
        solver_configs = generate_solver_configs(config.cvrp, num_workers)
        
        # Подготвяме аргументи за всеки работник
        worker_args = []
        for i, cvrp_config in enumerate(solver_configs):
            # Подаваме само необходимите части от конфигурацията, а не целия обект
            # Превръщаме ги в речници, за да избегнем pickling грешки.
            args = (
                warehouse_allocation,
                asdict(cvrp_config),
                asdict(config.locations),
                distance_matrix, # Подаваме готовата матрица
                i + 1
            )
            worker_args.append(args)

        with Pool(processes=num_workers) as pool:
            results = pool.map(solve_cvrp_worker, worker_args)
        
        valid_solutions = [sol for sol in results if sol is not None]
        
        if valid_solutions:
            # ИЗБИРАМЕ ПОБЕДИТЕЛЯ ПО НАЙ-ГОЛЯМ ОБСЛУЖЕН ОБЕМ
            for sol in valid_solutions:
                 sol.total_served_volume = sum(r.total_volume for r in sol.routes)

            best_solution = max(valid_solutions, key=lambda s: s.total_served_volume)
            
            logger.info(f"🏆 Избрано е най-доброто решение по ОБЕМ от {len(valid_solutions)} намерени, "
                        f"с обслужен обем: {best_solution.total_served_volume:.2f} ст.")
        else:
            logger.error("Всички паралелни работници се провалиха. Не е намерено решение.")

    else:
        # ЕДИНИЧЕН РЕЖИМ (опростен)
        logger.info("⚙️ Стартирам в единичен режим.")
        best_solution = solve_cvrp_worker((
            warehouse_allocation, 
            asdict(config.cvrp), 
            asdict(config.locations),
            distance_matrix,
            1
        ))

    if best_solution:
        execution_time = time.time() - start_time
        process_results(best_solution, input_data, warehouse_allocation, execution_time)
        print("\n✅ CVRP оптимизация завършена успешно!")
    else:
        logger.error("❌ Не успях да намеря решение на проблема.")
        print("\n❌ CVRP оптимизация завършена с грешки!")
        sys.exit(1)


if __name__ == "__main__":
    main() 
