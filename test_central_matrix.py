"""
Тест на системата за централна матрица
Демонстрира как да използваме предварително генерирана матрица вместо OSRM заявки
"""

import logging
import time
from osrm_client import (
    build_and_save_central_matrix, 
    get_central_matrix_info, 
    get_distance_matrix_from_central_cache
)
from input_handler import InputHandler
from cvrp_solver import CVRPSolver
from warehouse_manager import WarehouseManager

# Настройка на логирането
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_central_matrix_info():
    """Тества информацията за централната матрица"""
    logger.info("="*60)
    logger.info("ИНФОРМАЦИЯ ЗА ЦЕНТРАЛНАТА МАТРИЦА")
    logger.info("="*60)
    
    info = get_central_matrix_info()
    
    if info['exists']:
        logger.info(f"✅ Централна матрица НАЛИЧНА:")
        logger.info(f"   📊 Локации: {info['locations_count']}")
        logger.info(f"   📍 Депо: {info['depot_location']}")
        logger.info(f"   💾 Кеш записи: {info['cache_entries']}")
        logger.info(f"   📁 Размер файл: {info['cache_file_size']/1024/1024:.1f} MB")
    else:
        logger.info(f"❌ Централна матрица НЕ е налична")
        logger.info(f"   💾 Кеш записи: {info.get('cache_entries', 0)}")
        if 'error' in info:
            logger.error(f"   ⚠️ Грешка: {info['error']}")


def test_build_central_matrix():
    """Тества създаването на централна матрица"""
    logger.info("="*60) 
    logger.info("СЪЗДАВАНЕ НА ЦЕНТРАЛНА МАТРИЦА")
    logger.info("="*60)
    
    start_time = time.time()
    success = build_and_save_central_matrix()
    end_time = time.time()
    
    if success:
        logger.info(f"✅ Централна матрица създадена за {end_time - start_time:.2f} секунди")
    else:
        logger.error(f"❌ Неуспешно създаване на централна матрица")
    
    return success


def test_cvrp_with_central_matrix():
    """Тества CVRP с използване на централната матрица"""
    logger.info("="*60)
    logger.info("CVRP С ЦЕНТРАЛНА МАТРИЦА")
    logger.info("="*60)
    
    try:
        # Зареждаме данните
        handler = InputHandler()
        input_data = handler.load_data()
        
        # Разпределение
        warehouse_manager = WarehouseManager()
        allocation = warehouse_manager.allocate_customers(input_data)
        
        logger.info(f"Клиенти за превозни средства: {len(allocation.vehicle_customers)}")
        
        # CVRP решение
        solver = CVRPSolver()
        start_time = time.time()
        
        solution = solver.solve(allocation, input_data.depot_location)
        
        end_time = time.time()
        
        logger.info(f"✅ CVRP решен за {end_time - start_time:.2f} секунди")
        logger.info(f"   🚛 Превозни средства: {solution.total_vehicles_used}")
        logger.info(f"   📏 Общо разстояние: {solution.total_distance_km:.2f} км")
        logger.info(f"   ⏱️ Общо време: {solution.total_time_minutes:.1f} минути")
        
        solver.close()
        
    except Exception as e:
        logger.error(f"Грешка при тест на CVRP: {e}")


def test_speed_comparison():
    """Сравнява скоростта с и без централна матрица"""
    logger.info("="*60)
    logger.info("ТЕСТ НА СКОРОСТ: КЕША срещу OSRM ЗАЯВКИ")
    logger.info("="*60)
    
    try:
        # Зареждаме малка част от данните за тест
        handler = InputHandler()
        input_data = handler.load_data()
        
        # Взимаме първите 20 клиента
        test_customers = input_data.customers[:20]
        depot = input_data.depot_location
        locations = [depot] + [c.coordinates for c in test_customers]
        
        logger.info(f"Тествам с {len(locations)} локации...")
        
        # Тест 1: От централния кеш
        logger.info("🏁 Тест 1: Използване на централния кеш")
        start_time = time.time()
        matrix_from_cache = get_distance_matrix_from_central_cache(locations)
        cache_time = time.time() - start_time
        
        if matrix_from_cache:
            logger.info(f"✅ Кеш: {cache_time:.4f} секунди")
        else:
            logger.info(f"❌ Няма данни в кеша")
        
        # Тест 2: Директна OSRM заявка
        logger.info("🏁 Тест 2: Директна OSRM заявка")
        from osrm_client import OSRMClient
        client = OSRMClient()
        
        start_time = time.time()
        matrix_from_osrm = client.get_distance_matrix(locations)
        osrm_time = time.time() - start_time
        client.close()
        
        logger.info(f"✅ OSRM: {osrm_time:.4f} секунди")
        
        # Сравнение
        if matrix_from_cache and cache_time > 0:
            speedup = osrm_time / cache_time
            logger.info(f"🚀 Ускорение: {speedup:.1f}x по-бързо с кеша!")
        
    except Exception as e:
        logger.error(f"Грешка при тест на скорост: {e}")


def main():
    """Главна функция за тестване"""
    logger.info("🚀 ЗАПОЧВАМ ТЕСТОВЕ НА ЦЕНТРАЛНАТА МАТРИЦА")
    
    # Тест 1: Информация
    test_central_matrix_info()
    
    # Тест 2: Създаване (ако няма)
    info = get_central_matrix_info()
    if not info['exists']:
        logger.info("\n💾 Няма централна матрица - създавам я...")
        test_build_central_matrix()
    
    # Тест 3: CVRP с централна матрица
    test_cvrp_with_central_matrix()
    
    # Тест 4: Сравнение на скорост
    test_speed_comparison()
    
    logger.info("="*60)
    logger.info("✅ ВСИЧКИ ТЕСТОВЕ ЗАВЪРШЕНИ")
    logger.info("="*60)


if __name__ == "__main__":
    main()
 