"""
Тест на новия прогрес бар за OR-Tools и OSRM
"""

from main import CVRPApplication

def test_progress_bar_short():
    """Тест с кратко timeout за демонстрация"""
    print("🧪 ТЕСТ НА ПРОГРЕС БАР")
    print("=" * 50)
    
    # Конфигурация за бърз тест (60 секунди)
    quick_config = {
        "cvrp": {
            "time_limit_seconds": 60,  # 1 минута за демо
            "log_search": False,       # изключваме verbose логове
        },
        "osrm": {
            "chunk_size": 50,          # по-малки chunks за demo
        }
    }
    
    print("⚙️ Използвам кратък timeout (60 секунди) за демонстрация")
    print("📊 Ще видите прогрес барове за:")
    print("   1. 📡 OSRM Matrix заявки (ако има chunking)")
    print("   2. 🔄 OR-Tools оптимизация")
    print()
    
    app = CVRPApplication()
    success = app.run_with_custom_config(quick_config, "data/input.xlsx")
    
    if success:
        print("✅ Тест завършен успешно!")
    else:
        print("❌ Грешка в теста")
    
    return success

def test_progress_bar_normal():
    """Тест с нормален timeout (5 минути)"""
    print("🧪 ТЕСТ С НОРМАЛЕН TIMEOUT")
    print("=" * 50)
    
    normal_config = {
        "cvrp": {
            "time_limit_seconds": 300,  # 5 минути
            "log_search": False,
        }
    }
    
    print("⚙️ Нормален timeout (300 секунди = 5 минути)")
    print()
    
    app = CVRPApplication()
    success = app.run_with_custom_config(normal_config, "data/input.xlsx")
    
    return success

def demonstrate_progress_features():
    """Демонстрира характеристиките на прогрес бара"""
    print("📊 ХАРАКТЕРИСТИКИ НА ПРОГРЕС БАРА:")
    print("=" * 60)
    
    print("🔄 OR-Tools прогрес бар показва:")
    print("   • Текущо време / максимално време")
    print("   • Брой намерени решения")
    print("   • Най-доброто разстояние в км")
    print("   • Оставащо време")
    print("   • Визуален индикатор за прогрес")
    print()
    
    print("📡 OSRM прогрес бар показва:")
    print("   • Брой обработени chunks")
    print("   • Текущ chunk (координати)")
    print("   • Размер на chunk (брой локации)")
    print("   • Скорост на обработка")
    print()
    
    print("⏱️ ВРЕМЕВИ ЕТАПИ:")
    print("   1. OSRM заявки: 30-120 сек за 150-250 клиента")
    print("   2. OR-Tools първо решение: 30-90 сек") 
    print("   3. OR-Tools оптимизация: до 20 минути")
    print()

if __name__ == "__main__":
    demonstrate_progress_features()
    
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "short":
            test_progress_bar_short()
        elif sys.argv[1] == "normal":
            test_progress_bar_normal()
    else:
        print("🚀 За тестване:")
        print("   py test_progress_bar.py short   # Кратък тест (60 сек)")
        print("   py test_progress_bar.py normal  # Нормален тест (5 мин)")
        print()
        
        # Стартираме кратък тест по подразбиране
        test_progress_bar_short() 