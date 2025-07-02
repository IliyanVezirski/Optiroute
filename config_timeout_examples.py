"""
Примери за конфигуриране на OR-Tools timeout според различни сценарии
"""

from config import get_config, CVRPConfig
from main import CVRPApplication

def quick_optimization_config():
    """Бърза оптимизация за тестване - 60 секунди"""
    return {
        "cvrp": {
            "time_limit_seconds": 60,  # 1 минута
            "first_solution_strategy": "PATH_CHEAPEST_ARC",
            "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
            "log_search": True
        }
    }

def standard_business_config():
    """Стандартна бизнес оптимизация - 5 минути"""
    return {
        "cvrp": {
            "time_limit_seconds": 300,  # 5 минути (current)
            "first_solution_strategy": "PATH_CHEAPEST_ARC", 
            "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
            "log_search": True
        }
    }

def thorough_optimization_config():
    """Задълбочена оптимизация - 15 минути"""
    return {
        "cvrp": {
            "time_limit_seconds": 900,  # 15 минути
            "first_solution_strategy": "PATH_CHEAPEST_ARC",
            "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH", 
            "log_search": True
        }
    }

def maximum_optimization_config():
    """Максимална оптимизация - 30 минути"""
    return {
        "cvrp": {
            "time_limit_seconds": 1800,  # 30 минути
            "first_solution_strategy": "AUTOMATIC",
            "local_search_metaheuristic": "SIMULATED_ANNEALING",
            "log_search": True
        }
    }

def adaptive_timeout_by_problem_size(num_customers):
    """Адаптивен timeout според броя клиенти"""
    if num_customers <= 20:
        timeout = 60        # 1 минута за малки проблеми
    elif num_customers <= 50:
        timeout = 300       # 5 минути за средни проблеми  
    elif num_customers <= 100:
        timeout = 900       # 15 минути за големи проблеми
    else:
        timeout = 1800      # 30 минути за много големи проблеми
    
    return {
        "cvrp": {
            "time_limit_seconds": timeout,
            "first_solution_strategy": "PATH_CHEAPEST_ARC",
            "local_search_metaheuristic": "GUIDED_LOCAL_SEARCH",
            "log_search": True
        }
    }

def run_with_custom_timeout(timeout_seconds, input_file=None):
    """Стартира оптимизация с персонализиран timeout"""
    print(f"🔄 Стартиране с timeout: {timeout_seconds} секунди ({timeout_seconds/60:.1f} минути)")
    
    custom_config = {
        "cvrp": {
            "time_limit_seconds": timeout_seconds,
            "log_search": True  # за да видите прогреса
        }
    }
    
    app = CVRPApplication()
    success = app.run_with_custom_config(custom_config, input_file)
    
    return success

def benchmark_different_timeouts(input_file=None):
    """Тествa различни timeout стойности за сравнение"""
    timeouts = [60, 180, 300, 600, 900]  # 1мин, 3мин, 5мин, 10мин, 15мин
    
    print("🧪 BENCHMARK НА РАЗЛИЧНИ TIMEOUT СТОЙНОСТИ")
    print("=" * 60)
    
    results = []
    
    for timeout in timeouts:
        print(f"\n🔄 Тестване с timeout: {timeout} секунди")
        print("-" * 40)
        
        import time
        start_time = time.time()
        
        success = run_with_custom_timeout(timeout, input_file)
        
        elapsed_time = time.time() - start_time
        
        result = {
            "timeout": timeout,
            "success": success,
            "actual_time": elapsed_time
        }
        results.append(result)
        
        print(f"✅ Резултат: {'Успешно' if success else 'Неуспешно'}")
        print(f"⏱️ Действително време: {elapsed_time:.1f} секунди")
    
    print(f"\n📊 ОБОБЩЕНИЕ НА РЕЗУЛТАТИТЕ:")
    print("-" * 40)
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['timeout']}s → {result['actual_time']:.1f}s реално време")
    
    return results

# Препоръки според случая на употреба
TIMEOUT_RECOMMENDATIONS = {
    "development_testing": {
        "timeout": 60,
        "description": "Бързо тестване по време на разработка"
    },
    "daily_operations": {
        "timeout": 300, 
        "description": "Ежедневни бизнес операции - баланс скорост/качество"
    },
    "weekly_planning": {
        "timeout": 900,
        "description": "Седмично планиране - по-добро качество"
    },
    "strategic_optimization": {
        "timeout": 1800,
        "description": "Стратегическо планиране - максимално качество"
    },
    "research_analysis": {
        "timeout": 3600,
        "description": "Изследователски анализ - най-добри резултати"
    }
}

def print_timeout_recommendations():
    """Отпечатва препоръки за timeout"""
    print("💡 ПРЕПОРЪКИ ЗА OR-TOOLS TIMEOUT:")
    print("=" * 50)
    
    for use_case, config in TIMEOUT_RECOMMENDATIONS.items():
        timeout_minutes = config["timeout"] / 60
        print(f"\n🎯 {use_case.replace('_', ' ').title()}:")
        print(f"   ⏱️ Timeout: {config['timeout']} секунди ({timeout_minutes:.1f} минути)")
        print(f"   📝 Описание: {config['description']}")

if __name__ == "__main__":
    print_timeout_recommendations()
    
    print(f"\n🔧 За промяна на timeout, редактирайте config.py:")
    print("   cvrp.time_limit_seconds = 900  # 15 минути")
    
    print(f"\n🧪 За тестване на различни timeout стойности:")
    print("   py config_timeout_examples.py")
    print("   benchmark_different_timeouts('data/sample.xlsx')") 