"""
Модул за управление на складова логика в CVRP
Управлява разпределението на заявки между превозни средства и склад
"""

from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
import logging
from config import get_config, WarehouseConfig, VehicleConfig
from input_handler import Customer, InputData

logger = logging.getLogger(__name__)


@dataclass
class WarehouseAllocation:
    """Разпределение между превозни средства и склад"""
    vehicle_customers: List[Customer]  # клиенти за превозни средства
    warehouse_customers: List[Customer]  # клиенти за склад
    total_vehicle_capacity: int
    total_vehicle_volume: float
    warehouse_volume: float
    capacity_utilization: float


class WarehouseManager:
    """Мениджър за складова логика"""
    
    def __init__(self, config: Optional[WarehouseConfig] = None):
        self.config = config or get_config().warehouse
        self.vehicle_configs = get_config().vehicles
    
    def allocate_customers(self, input_data: InputData) -> WarehouseAllocation:
        """Разпределя клиентите между превозни средства и склад"""
        logger.info("Започвам разпределение на клиенти")
        
        # Изчисляване на общия капацитет
        total_capacity = self._calculate_total_vehicle_capacity()
        
        # Сортиране на клиентите
        sorted_customers = self._sort_customers(input_data.customers)
        
        # Разпределение - ВИНАГИ използваме warehouse логиката за 80% правило
        if self.config.enable_warehouse:
            return self._allocate_with_warehouse(sorted_customers, total_capacity)
        else:
            # Изчисляваме обема само на клиентите за автобуси
            vehicle_volume = sum(c.volume for c in sorted_customers)
            return WarehouseAllocation(
                vehicle_customers=sorted_customers,
                warehouse_customers=[],
                total_vehicle_capacity=total_capacity,
                total_vehicle_volume=vehicle_volume,
                warehouse_volume=0.0,
                capacity_utilization=vehicle_volume / total_capacity if total_capacity > 0 else 0
            )
    
    def _calculate_total_vehicle_capacity(self) -> int:
        """Изчислява общия капацитет на всички включени превозни средства"""
        total_capacity = 0
        
        if self.vehicle_configs:
            for vehicle in self.vehicle_configs:
                if vehicle.enabled:
                    total_capacity += vehicle.capacity * vehicle.count
        
        return total_capacity
    
    def _sort_customers(self, customers: List[Customer]) -> List[Customer]:
        """Сортира клиентите според конфигурацията"""
        if self.config.sort_by_volume:
            return sorted(customers, key=lambda c: c.volume)
        else:
            return customers.copy()
    
    def _allocate_with_warehouse(self, customers: List[Customer], 
                               total_capacity: int) -> WarehouseAllocation:
        """Разпределя клиенти с използване на склад (най-големите в склада)"""
        
        # НОВА ЛОГИКА: Най-големите клиенти отиват в склада
        vehicle_customers, warehouse_customers = self._allocate_largest_to_warehouse(customers, total_capacity)
        
        current_volume = sum(c.volume for c in vehicle_customers)
        warehouse_volume = sum(c.volume for c in warehouse_customers)
        
        logger.info(f"Оптимизирано разпределение: {len(vehicle_customers)} за превозни средства, "
                   f"{len(warehouse_customers)} за склад")
        logger.info(f"Използване на капацитета: {current_volume}/{total_capacity} ({current_volume/total_capacity:.1%})")
        
        return WarehouseAllocation(
            vehicle_customers=vehicle_customers,
            warehouse_customers=warehouse_customers,
            total_vehicle_capacity=total_capacity,
            total_vehicle_volume=current_volume,
            warehouse_volume=warehouse_volume,
            capacity_utilization=current_volume / total_capacity if total_capacity > 0 else 0
        )
    
    def _knapsack_allocation(self, customers: List[Customer], capacity: int) -> Optional[Tuple[List[Customer], List[Customer]]]:
        """Използва knapsack-подобен алгоритъм за оптимално разпределение"""
        try:
            n = len(customers)
            if n == 0:
                return [], []
            
            # Преобразуваме в цели числа за knapsack алгоритъма 
            volumes = [int(c.volume * 10) for c in customers]  # умножаваме по 10 за точност
            capacity_int = int(capacity * 10)
            
            # Опростен greedy knapsack алгоритъм
            # Сортираме по ефективност (обем/1 - малко по-голям приоритет за по-големи клиенти)
            indexed_customers = [(i, customers[i], volumes[i]) for i in range(n)]
            indexed_customers.sort(key=lambda x: x[2], reverse=True)  # големи първо за по-добро запълване
            
            selected = []
            current_capacity = 0
            
            # Greedily добавяме клиенти
            for idx, customer, volume in indexed_customers:
                if current_capacity + volume <= capacity_int:
                    selected.append(idx)
                    current_capacity += volume
            
            # Разделяме на vehicle и warehouse клиенти
            vehicle_customers = [customers[i] for i in selected]
            warehouse_customers = [customers[i] for i in range(n) if i not in selected]
            
            return vehicle_customers, warehouse_customers
            
        except Exception as e:
            logger.error(f"Грешка в knapsack алгоритъм: {e}")
            return None
    
    def _simple_allocation(self, customers: List[Customer], total_capacity: int) -> Tuple[List[Customer], List[Customer]]:
        """Проста логика за разпределение (fallback)"""
        vehicle_customers = []
        warehouse_customers = []
        current_volume = 0.0
        
        for customer in customers:
            if current_volume + customer.volume <= total_capacity:
                vehicle_customers.append(customer)
                current_volume += customer.volume
            else:
                warehouse_customers.append(customer)
        
        return vehicle_customers, warehouse_customers
    
    def _allocate_largest_to_warehouse(self, customers: List[Customer], total_capacity: int) -> Tuple[List[Customer], List[Customer]]:
        """
        Разпределя клиенти, като първо отделя тези, които са твърде големи, за да се поберат
        в който и да е наличен бус.
        """
        logger.info("✅ Активирано е предварително филтриране на заявки.")

        if not self.vehicle_configs:
            logger.warning("Няма дефинирани превозни средства. Всички клиенти отиват към solver-а.")
            return customers, []

        # 1. Намираме капацитета на НАЙ-ГОЛЕМИЯ единичен бус
        max_vehicle_capacity = 0
        for v_config in self.vehicle_configs:
            if v_config.enabled and v_config.capacity > max_vehicle_capacity:
                max_vehicle_capacity = v_config.capacity
        
        if max_vehicle_capacity == 0:
            logger.warning("Няма налични превозни средства с капацитет > 0.")
            return customers, []
            
        logger.info(f"ДЕБЪГ: Максимален капацитет на единичен бус: {max_vehicle_capacity}")

        # 2. Определяме прага за "голяма" заявка
        large_request_threshold_volume = max_vehicle_capacity * self.config.large_request_threshold
        logger.info(f"ДЕБЪГ: Праг за 'голяма' заявка (над {self.config.large_request_threshold:.0%}): {large_request_threshold_volume:.2f} ст.")

        vehicle_customers = []
        warehouse_customers = []

        for customer in customers:
            # 3. Проверяваме дали клиентът е АБСОЛЮТНО невъзможен
            if customer.volume > max_vehicle_capacity:
                logger.warning(f"ДЕБЪГ: Клиент '{customer.name}' (обем: {customer.volume}) е твърде голям "
                               f"(надвишава {max_vehicle_capacity}) и се изпраща директно в склада.")
                warehouse_customers.append(customer)
                continue

            # 4. Проверяваме дали да го преместим в склада според конфигурацията
            if self.config.move_largest_to_warehouse and customer.volume > large_request_threshold_volume:
                logger.info(f"ДЕБЪГ: Клиент '{customer.name}' (обем: {customer.volume}) се счита за 'голям' и се изпраща в склада.")
                warehouse_customers.append(customer)
            else:
                vehicle_customers.append(customer)

        # Финални изчисления
        vehicle_volume = sum(c.volume for c in vehicle_customers)
        warehouse_volume = sum(c.volume for c in warehouse_customers)
        actual_utilization = vehicle_volume / total_capacity if total_capacity > 0 else 0
        
        # Логиране на резултата
        logger.info(f"Предварително разпределение завършено:")
        logger.info(f"  🚛 Клиенти за Solver: {len(vehicle_customers)} ({vehicle_volume:.1f} ст.)")
        logger.info(f"  🏭 Клиенти за Склад (твърде големи): {len(warehouse_customers)} ({warehouse_volume:.1f} ст.)")
        logger.info(f"  📊 Потенциално използване на капацитет: {actual_utilization:.1%}")

        # Проверка за валидност
        total_input_volume = sum(c.volume for c in customers)
        total_output_volume = vehicle_volume + warehouse_volume
        if abs(total_input_volume - total_output_volume) > 0.1:
            logger.error(f"❌ Грешка в разпределението: Input {total_input_volume:.1f} != Output {total_output_volume:.1f}")
        
        return vehicle_customers, warehouse_customers
    
    def optimize_allocation(self, allocation: WarehouseAllocation) -> WarehouseAllocation:
        """
        Този метод вече не се използва.
        Цялата логика за избор на клиенти е прехвърлена към OR-Tools solver-а,
        който взима оптимално решение кои клиенти да пропусне.
        """
        logger.info("⏩ Методът optimize_allocation се пропуска (логиката е в solver-а).")
        return allocation
    
    def get_allocation_summary(self, allocation: WarehouseAllocation) -> Dict[str, Any]:
        """Връща резюме на разпределението"""
        total_customers = len(allocation.vehicle_customers) + len(allocation.warehouse_customers)
        return {
            'total_customers': total_customers,
            'vehicle_customers_count': len(allocation.vehicle_customers),
            'warehouse_customers_count': len(allocation.warehouse_customers),
            'total_vehicle_capacity': allocation.total_vehicle_capacity,
            'vehicle_volume_used': allocation.total_vehicle_volume,
            'warehouse_volume': allocation.warehouse_volume,
            'capacity_utilization_percent': allocation.capacity_utilization * 100,
            'available_capacity': allocation.total_vehicle_capacity - allocation.total_vehicle_volume,
            'warehouse_percentage': (len(allocation.warehouse_customers) / total_customers) * 100 if total_customers > 0 else 0
        }
    
    def validate_allocation(self, allocation: WarehouseAllocation) -> bool:
        """Валидира разпределението"""
        # Проверка дали обемът не надвишава капацитета
        if allocation.total_vehicle_volume > allocation.total_vehicle_capacity:
            logger.error("Обемът за превозни средства надвишава капацитета")
            return False
        
        # Проверка за дублирани клиенти
        all_customer_ids = [c.id for c in allocation.vehicle_customers] + [c.id for c in allocation.warehouse_customers]
        if len(all_customer_ids) != len(set(all_customer_ids)):
            logger.error("Открити дублирани клиенти в разпределението")
            return False
        
        return True
    
    def can_fit_in_vehicles(self, customers: List[Customer]) -> bool:
        """Проверява дали клиентите могат да се поберат в превозните средства"""
        total_volume = sum(c.volume for c in customers)
        total_capacity = self._calculate_total_vehicle_capacity()
        
        return total_volume <= total_capacity


# Удобна функция за използване
def allocate_customers_to_vehicles_and_warehouse(input_data: InputData) -> WarehouseAllocation:
    """Удобна функция за разпределение на клиенти"""
    manager = WarehouseManager()
    allocation = manager.allocate_customers(input_data)
    
    # Оптимизация на разпределението
    optimized_allocation = manager.optimize_allocation(allocation)
    
    # Валидация
    if not manager.validate_allocation(optimized_allocation):
        raise ValueError("Невалидно разпределение на клиенти")
    
    # Логиране на резюмето
    summary = manager.get_allocation_summary(optimized_allocation)
    logger.info(f"Резюме на разпределението: {summary}")
    
    return optimized_allocation 