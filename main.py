"""
Главен файл за CVRP програма
Координира всички модули за решаване на Vehicle Routing Problem
"""

import logging
import sys
import time
from typing import Optional
from config import get_config, config_manager
from input_handler import InputHandler
from warehouse_manager import WarehouseManager
from cvrp_solver import CVRPSolver
from output_handler import OutputHandler


def setup_logging():
    """Настройва логирането"""
    config = get_config()
    
    # Настройка на logging format
    formatter = logging.Formatter(config.logging.log_format)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.logging.log_level))
    
    # Console handler
    if config.logging.enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if config.logging.enable_file_logging:
        import os
        os.makedirs(os.path.dirname(config.logging.log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(config.logging.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


class CVRPApplication:
    """Главно приложение за CVRP"""
    
    def __init__(self):
        self.config = get_config()
        self.input_handler = InputHandler()
        self.warehouse_manager = WarehouseManager()
        self.cvrp_solver = CVRPSolver()
        self.output_handler = OutputHandler()
        self.logger = logging.getLogger(__name__)
    
    def run(self, input_file: Optional[str] = None) -> bool:
        """Стартира цялостния процес на CVRP оптимизация"""
        try:
            self.logger.info("="*60)
            self.logger.info("СТАРТИРАНЕ НА CVRP ОПТИМИЗАТОР")
            self.logger.info("="*60)
            
            start_time = time.time()
            
            # Стъпка 1: Зареждане на входните данни
            self.logger.info("Стъпка 1: Зареждане на входни данни")
            input_data = self.input_handler.load_data(input_file)
            
            if not input_data.customers:
                self.logger.error("Няма валидни клиенти в входните данни")
                return False
            
            self.logger.info(f"Заредени {len(input_data.customers)} клиенти с общ обем {input_data.total_volume:.2f} ст.")
            
            # Стъпка 2: Разпределение склад/превозни средства
            self.logger.info("Стъпка 2: Разпределение между склад и превозни средства")
            warehouse_allocation = self.warehouse_manager.allocate_customers(input_data)
            
            # Оптимизация на разпределението
            warehouse_allocation = self.warehouse_manager.optimize_allocation(warehouse_allocation)
            
            self.logger.info(f"Клиенти за превозни средства: {len(warehouse_allocation.vehicle_customers)}")
            self.logger.info(f"Клиенти за склад: {len(warehouse_allocation.warehouse_customers)}")
            self.logger.info(f"Използване на капацитета: {warehouse_allocation.capacity_utilization*100:.1f}%")
            
            # Стъпка 3: CVRP оптимизация
            self.logger.info("Стъпка 3: CVRP оптимизация на маршрутите")
            
            solution = self.cvrp_solver.solve(warehouse_allocation, input_data.depot_location)
            
            self.logger.info(f"CVRP решение: {solution.total_vehicles_used} превозни средства")
            self.logger.info(f"Общо разстояние: {solution.total_distance_km:.2f} км")
            self.logger.info(f"Общо време: {solution.total_time_minutes:.1f} минути")
            
            # Стъпка 4: Генериране на изходи
            self.logger.info("Стъпка 4: Генериране на изходни файлове")
            output_files = self.output_handler.generate_all_outputs(
                solution, warehouse_allocation, input_data.depot_location
            )
            
            # Резюме
            self._print_summary(input_data, warehouse_allocation, solution, output_files)
            
            execution_time = time.time() - start_time
            self.logger.info(f"Общо време за изпълнение: {execution_time:.2f} секунди")
            self.logger.info("="*60)
            self.logger.info("CVRP ОПТИМИЗАЦИЯ ЗАВЪРШЕНА УСПЕШНО")
            self.logger.info("="*60)
            
            cnt_center = sum(1 for c in input_data.customers if "Център" in c.name)
            cnt_ext    = sum(1 for c in input_data.customers if "Външен" in c.name)
            self.logger.info(f"Клиенти Център={cnt_center}, Външен={cnt_ext}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Грешка при изпълнение на CVRP оптимизация: {e}")
            if self.config.debug_mode:
                import traceback
                self.logger.error(traceback.format_exc())
            return False
        
        finally:
            # Затваряне на ресурсите
            self.cvrp_solver.close()
    
    def _print_summary(self, input_data, warehouse_allocation, final_params, output_files):
        """Отпечатва резюме на изпълнението"""
        self.logger.info("\n" + "="*50)
        self.logger.info("РЕЗЮМЕ НА ОПТИМИЗАЦИЯТА")
        self.logger.info("="*50)
        
        # Входни данни
        self.logger.info("ВХОДНИ ДАННИ:")
        self.logger.info(f"  Общо клиенти: {len(input_data.customers)}")
        self.logger.info(f"  Общ обем: {input_data.total_volume:.2f} стотинки")
        self.logger.info(f"  Депо координати: {input_data.depot_location}")
        
        # Разпределение
        total_unserviced = len(warehouse_allocation.warehouse_customers) + len(final_params.dropped_customers)
        self.logger.info("\nРАЗПРЕДЕЛЕНИЕ:")
        self.logger.info(f"  Клиенти за превозни средства: {len(warehouse_allocation.vehicle_customers)}")
        self.logger.info(f"  Необслужени клиенти (склад/пропуснати): {total_unserviced}")
        self.logger.info(f"  Капацитет превозни средства: {warehouse_allocation.total_vehicle_capacity} ст.")
        self.logger.info(f"  Използван капацитет: {warehouse_allocation.total_vehicle_volume:.2f} ст.")
        self.logger.info(f"  Процент използване: {warehouse_allocation.capacity_utilization*100:.1f}%")
        
        # CVRP решение
        self.logger.info("\nCVRP РЕШЕНИЕ:")
        self.logger.info(f"  Използвани превозни средства: {final_params.total_vehicles_used}")
        self.logger.info(f"  Общо разстояние: {final_params.total_distance_km:.2f} км")
        self.logger.info(f"  Общо време: {final_params.total_time_minutes:.1f} минути")
        self.logger.info(f"  Fitness оценка: {final_params.fitness_score:.2f}")
        self.logger.info(f"  Допустимо решение: {'Да' if final_params.is_feasible else 'Не'}")
        
        # Детайли по маршрути
        if final_params.routes:
            self.logger.info("\nДЕТАЙЛИ ПО МАРШРУТИ:")
            for i, route in enumerate(final_params.routes):
                vehicle_name = route.vehicle_type.value.replace('_', ' ').title()
                self.logger.info(f"  Маршрут {i+1} ({vehicle_name}):")
                self.logger.info(f"    Клиенти: {len(route.customers)}")
                self.logger.info(f"    Обем: {route.total_volume:.2f} ст.")
                self.logger.info(f"    Разстояние: {route.total_distance_km:.2f} км")
                self.logger.info(f"    Време: {route.total_time_minutes:.1f} мин")
        
        # Изходни файлове
        self.logger.info("\nГЕНЕРИРАНИ ФАЙЛОВЕ:")
        for file_type, file_path in output_files.items():
            file_type_name = file_type.replace('_', ' ').title()
            self.logger.info(f"  {file_type_name}: {file_path}")
        
        self.logger.info("="*50)
    
    def run_with_custom_config(self, config_updates: dict, input_file: Optional[str] = None) -> bool:
        """Стартира с персонализирани настройки"""
        # Запазване на оригиналната конфигурация
        original_config = self.config
        
        try:
            # Зареждане на нова конфигурация
            updated_config = config_manager.load_config(config_updates)
            
            # Обновяване на компонентите
            self.input_handler = InputHandler()
            self.warehouse_manager = WarehouseManager()
            self.cvrp_solver = CVRPSolver()
            self.output_handler = OutputHandler()
            
            return self.run(input_file)
            
        finally:
            # Възстановяване на оригиналната конфигурация
            config_manager.config = original_config


def main():
    """Главна функция"""
    # Настройка на логирането
    setup_logging()
    
    # Създаване и стартиране на приложението
    app = CVRPApplication()
    
    # Проверка за аргументи от командния ред
    input_file = None
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    success = app.run(input_file)
    
    if success:
        print("\n✅ CVRP оптимизация завършена успешно!")
        print("Проверете генерираните файлове в output/ директорията.")
    else:
        print("\n❌ CVRP оптимизация завършена с грешки!")
        print("Проверете лог файла за повече детайли.")
        sys.exit(1)


if __name__ == "__main__":
    main() 