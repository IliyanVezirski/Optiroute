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
        
        # Разпределение
        if self.config.enable_warehouse and input_data.total_volume > total_capacity:
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
        """Разпределя клиенти оптимално за OR-Tools (max 85% използване)"""
        logger.info("Започвам разпределение: оптимизирано за OR-Tools")
        
        # Сортираме от най-голям към най-малък
        sorted_customers = sorted(customers, key=lambda c: c.volume, reverse=True)
        
        # Целеви капацитет за OR-Tools (85% от общия)
        target_capacity = int(total_capacity * 0.85)
        logger.info(f"🎯 Целеви капацитет за OR-Tools: {target_capacity} ст. (85% от {total_capacity})")
        
        vehicle_customers = []
        warehouse_customers = []
        current_volume = 0.0
        
        # Преминаваме от най-малкия към най-големия за по-добро запълване
        reversed_customers = sorted_customers[::-1]  # от малък към голям
        
        for customer in reversed_customers:
            if current_volume + customer.volume <= target_capacity:
                vehicle_customers.append(customer)
                current_volume += customer.volume
                logger.debug(f"Клиент {customer.id} ({customer.volume:.1f} ст.) → АВТОБУСИ")
            else:
                warehouse_customers.append(customer)
                logger.debug(f"Клиент {customer.id} ({customer.volume:.1f} ст.) → СКЛАД")
        
        # Финални изчисления
        vehicle_volume = sum(c.volume for c in vehicle_customers)
        warehouse_volume = sum(c.volume for c in warehouse_customers)
        actual_utilization = vehicle_volume / total_capacity
        
        # Логиране на резултата
        logger.info(f"Разпределение завършено:")
        logger.info(f"  🚛 Автобуси: {len(vehicle_customers)} клиента ({vehicle_volume:.1f} ст.)")
        logger.info(f"  🏭 Склад: {len(warehouse_customers)} клиента ({warehouse_volume:.1f} ст.)")
        logger.info(f"  📊 Използване капацитет: {actual_utilization:.1%} (цел: 85%)")
        logger.info(f"  🤖 OR-Tools готовност: {'✅ Готов' if actual_utilization <= 0.90 else '⚠️ Рискован'}")
        
        return vehicle_customers, warehouse_customers
    
    def optimize_allocation(self, allocation: WarehouseAllocation) -> WarehouseAllocation:
        """Оптимизира разпределението"""
        if not allocation.warehouse_customers:
            return allocation
        
        logger.info("Оптимизирам разпределението...")
        
        # Опитваме да преместим някои клиенти от склада в превозните средства
        # ако има налично място
        available_capacity = allocation.total_vehicle_capacity - allocation.total_vehicle_volume
        
        if available_capacity <= 0:
            return allocation
        
        # Сортираме складовите клиенти по обем (от малък към голям)
        warehouse_sorted = sorted(allocation.warehouse_customers, key=lambda c: c.volume)
        
        optimized_vehicle_customers = allocation.vehicle_customers.copy()
        optimized_warehouse_customers = []
        current_volume = allocation.total_vehicle_volume
        
        for customer in warehouse_sorted:
            if current_volume + customer.volume <= allocation.total_vehicle_capacity:
                optimized_vehicle_customers.append(customer)
                current_volume += customer.volume
                logger.info(f"Преместен клиент {customer.id} от склад в превозни средства")
            else:
                optimized_warehouse_customers.append(customer)
        
        new_warehouse_volume = sum(c.volume for c in optimized_warehouse_customers)
        
        return WarehouseAllocation(
            vehicle_customers=optimized_vehicle_customers,
            warehouse_customers=optimized_warehouse_customers,
            total_vehicle_capacity=allocation.total_vehicle_capacity,
            total_vehicle_volume=current_volume,
            warehouse_volume=new_warehouse_volume,
            capacity_utilization=current_volume / allocation.total_vehicle_capacity
        )
    
    def get_allocation_summary(self, allocation: WarehouseAllocation) -> Dict[str, Any]:
        """Връща резюме на разпределението"""
        return {
            'total_customers': len(allocation.vehicle_customers) + len(allocation.warehouse_customers),
            'vehicle_customers_count': len(allocation.vehicle_customers),
            'warehouse_customers_count': len(allocation.warehouse_customers),
            'total_vehicle_capacity': allocation.total_vehicle_capacity,
            'vehicle_volume_used': allocation.total_vehicle_volume,
            'warehouse_volume': allocation.warehouse_volume,
            'capacity_utilization_percent': allocation.capacity_utilization * 100,
            'available_capacity': allocation.total_vehicle_capacity - allocation.total_vehicle_volume,
            'warehouse_percentage': (len(allocation.warehouse_customers) / 
                                   (len(allocation.vehicle_customers) + len(allocation.warehouse_customers)) * 100
                                   if (len(allocation.vehicle_customers) + len(allocation.warehouse_customers)) > 0 else 0)
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