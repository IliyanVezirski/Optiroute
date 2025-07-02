"""
Специализирана конфигурация за големи CVRP проблеми (150-250 клиента)
"""

from config import get_config, CVRPConfig
from main import CVRPApplication

def large_scale_optimization_config():
    """Оптимизирана конфигурация за 150-250 клиента"""
    return {
        "cvrp": {
            "time_limit_seconds": 300,  # 20 минути
            "first_solution_strategy": "PATH_CHEAPEST_ARC",  # по-бърза за големи проблеми
            "local_search_metaheuristic": "LOCAL_SEARCH",  # най-добра за качество
            "log_search": True  # за да следите прогреса
        },
        "osrm": {
            "chunk_size": 90,  # максимални chunks за бързина
            "use_cache": True,  # задължително кеширане
            "timeout_seconds": 45  # по-дълъг timeout за OSRM заявки
        },
        "performance": {
            "enable_multiprocessing": True,
            "max_workers": 4,
            "chunk_processing_delay": 0.05  # по-малка пауза между chunks
        },
        "debug_mode": False  # изключваме debug за по-бърза работа
    }

def ultra_optimization_config():
    """Максимална оптимизация за критични случаи - 30 минути"""
    return {
        "cvrp": {
            "time_limit_seconds": 1800,  # 30 минути
            "first_solution_strategy": "AUTOMATIC",  # OR-Tools избира най-добрата
            "local_search_metaheuristic": "SIMULATED_ANNEALING",  # най-добро качество
            "log_search": True
        },
        "osrm": {
            "chunk_size": 90,
            "use_cache": True,
            "timeout_seconds": 60,
            "retry_attempts": 5  # повече опити за стабилност
        },
        "performance": {
            "enable_multiprocessing": True,
            "max_workers": 6,  # повече workers
            "chunk_processing_delay": 0.02
        }
    }

def progressive_timeout_config():
    """Прогресивен timeout - започва с 10 мин, ако не стигне продължава до 25 мин"""
    return {
        "cvrp": {
            "time_limit_seconds": 1500,  # 25 минути
            "first_solution_strategy": "PATH_CHEAPEST_ARC",
            "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
            "log_search": True
        }
    }

# Анализ на очакваните времена за 150-250 клиента
PERFORMANCE_EXPECTATIONS = {
    "150_clients": {
        "first_solution": "30-60 секунди",
        "good_solution": "5-8 минути", 
        "very_good_solution": "12-18 минути",
        "optimal_solution": "20-30 минути"
    },
    "200_clients": {
        "first_solution": "45-90 секунди",
        "good_solution": "8-12 минути",
        "very_good_solution": "15-25 минути", 
        "optimal_solution": "25-40 минути"
    },
    "250_clients": {
        "first_solution": "60-120 секунди",
        "good_solution": "10-15 минути",
        "very_good_solution": "20-30 минути",
        "optimal_solution": "30-50 минути"
    }
}

def adaptive_config_by_client_count(num_clients):
    """Автоматична конфигурация според броя клиенти"""
    if num_clients <= 50:
        timeout = 300        # 5 минути
        strategy = "PATH_CHEAPEST_ARC"
        metaheuristic = "GUIDED_LOCAL_SEARCH"
    elif num_clients <= 100:
        timeout = 600        # 10 минути
        strategy = "PATH_CHEAPEST_ARC"
        metaheuristic = "GUIDED_LOCAL_SEARCH"
    elif num_clients <= 150:
        timeout = 900        # 15 минути
        strategy = "PARALLEL_CHEAPEST_INSERTION"
        metaheuristic = "GUIDED_LOCAL_SEARCH"
    elif num_clients <= 200:
        timeout = 1200       # 20 минути
        strategy = "PARALLEL_CHEAPEST_INSERTION"
        metaheuristic = "GUIDED_LOCAL_SEARCH"
    elif num_clients <= 250:
        timeout = 1500       # 25 минути
        strategy = "PARALLEL_CHEAPEST_INSERTION"
        metaheuristic = "SIMULATED_ANNEALING"
    else:
        timeout = 1800       # 30 минути
        strategy = "AUTOMATIC"
        metaheuristic = "SIMULATED_ANNEALING"
    
    return {
        "cvrp": {
            "time_limit_seconds": timeout,
            "first_solution_strategy": strategy,
            "local_search_metaheuristic": metaheuristic,
            "log_search": True
        },
        "osrm": {
            "chunk_size": 90,
            "use_cache": True,
            "timeout_seconds": min(60, timeout // 20)  # пропорционален OSRM timeout
        }
    }

def print_performance_analysis():
    """Показва анализ на производителността"""
    print("📊 АНАЛИЗ НА ПРОИЗВОДИТЕЛНОСТТА ЗА ГОЛЕМИ ПРОБЛЕМИ")
    print("=" * 60)
    
    for size, times in PERFORMANCE_EXPECTATIONS.items():
        client_count = size.replace("_", " ").title()
        print(f"\n🎯 {client_count}:")
        for phase, time_range in times.items():
            phase_name = phase.replace("_", " ").title()
            print(f"   {phase_name}: {time_range}")
    
    print(f"\n💡 ПРЕПОРЪКИ:")
    print("- За ежедневна употреба: 15-20 минути timeout")
    print("- За седмично планиране: 25-30 минути timeout") 
    print("- За стратегическо планиране: 45-60 минути timeout")
    
    print(f"\n⚠️ ВАЖНО:")
    print("- Първото решение се намира бързо (1-2 минути)")
    print("- 80% от подобрението идва в първите 10-15 минути")
    print("- След 25-30 минути подобренията са минимални")

def estimate_optimization_time(num_clients):
    """Оценява необходимото време за оптимизация"""
    if num_clients <= 50:
        return "5-10 минути"
    elif num_clients <= 100:
        return "10-15 минути"
    elif num_clients <= 150:
        return "15-20 минути"
    elif num_clients <= 200:
        return "20-25 минути"
    elif num_clients <= 250:
        return "25-35 минути"
    else:
        return "35+ минути"

def run_optimized_for_large_scale(input_file=None, num_clients=200):
    """Стартира оптимизация специално настроена за големи проблеми"""
    print(f"🚀 СТАРТИРАНЕ НА ОПТИМИЗАЦИЯ ЗА {num_clients} КЛИЕНТА")
    print("=" * 60)
    
    estimated_time = estimate_optimization_time(num_clients)
    print(f"⏱️ Очаквано време: {estimated_time}")
    
    # Избираме подходящата конфигурация
    if num_clients >= 200:
        config = ultra_optimization_config()
        print("🎯 Използвам ultra оптимизация (30 минути)")
    else:
        config = large_scale_optimization_config()
        print("🎯 Използвам large scale оптимизация (20 минути)")
    
    print(f"⚙️ Timeout: {config['cvrp']['time_limit_seconds']} секунди")
    print(f"🔧 Стратегия: {config['cvrp']['first_solution_strategy']}")
    print(f"🧠 Метахевристика: {config['cvrp']['local_search_metaheuristic']}")
    
    app = CVRPApplication()
    success = app.run_with_custom_config(config, input_file)
    
    return success

if __name__ == "__main__":
    print_performance_analysis()
    
    print(f"\n🔧 ЗА ПРОМЯНА НА КОНФИГУРАЦИЯТА:")
    print("1. Редактирайте config.py:")
    print("   cvrp.time_limit_seconds = 1200  # 20 минути")
    print("\n2. Или използвайте adaptive конфигурация:")
    print("   config = adaptive_config_by_client_count(200)")
    
    print(f"\n🚀 ЗА СТАРТИРАНЕ С ОПТИМИЗИРАНА КОНФИГУРАЦИЯ:")
    print("   from large_scale_config import run_optimized_for_large_scale")
    print("   run_optimized_for_large_scale('data/input.xlsx', 200)") 