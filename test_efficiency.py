"""
Тест за ефективността на новия OSRM клиент с големи datasets
"""

from osrm_client import OSRMClient
from config import get_config
import time
import random

def generate_test_locations(count: int, center_lat: float = 42.7, center_lon: float = 23.3, radius: float = 0.1):
    """Генерира тестови локации около център"""
    locations = []
    for _ in range(count):
        # Генериране на случайни координати в радиус
        lat = center_lat + random.uniform(-radius, radius)
        lon = center_lon + random.uniform(-radius, radius)
        locations.append((lat, lon))
    return locations

def test_efficiency():
    """Тестване на ефективността за различни размери"""
    
    print("🚀 Тест за ефективност на OSRM системата")
    print("=" * 60)
    
    # Тестови размери
    test_sizes = [10, 20, 50, 100, 200, 300]
    
    config = get_config()
    client = OSRMClient(config.osrm)
    
    print(f"⚙️  Настройки:")
    print(f"   Chunk size: {config.osrm.chunk_size}")
    print(f"   Max locations for OSRM: {getattr(config.osrm, 'max_locations_for_osrm', 50)}")
    print(f"   Smart chunking: {getattr(config.osrm, 'enable_smart_chunking', True)}")
    print()
    
    results = []
    
    for size in test_sizes:
        print(f"📊 Тестване с {size} локации...")
        
        # Генериране на тестови локации
        locations = generate_test_locations(size)
        
        # Измерване на времето
        start_time = time.time()
        
        try:
            matrix = client.get_distance_matrix(locations)
            end_time = time.time()
            duration = end_time - start_time
            
            # Проверка какъв метод е използван
            if size > getattr(config.osrm, 'max_locations_for_osrm', 50):
                method = "Приблизителни стойности"
            elif size <= 20:
                method = "OSRM (single)"
            else:
                method = "OSRM (chunked)"
            
            results.append({
                'size': size,
                'duration': duration,
                'method': method,
                'success': True
            })
            
            print(f"   ✅ {duration:.2f}s - {method}")
            print(f"      Matrix размер: {len(matrix.distances)}x{len(matrix.distances[0])}")
            
        except Exception as e:
            print(f"   ❌ Грешка: {e}")
            results.append({
                'size': size,
                'duration': 0,
                'method': "Грешка",
                'success': False
            })
        
        print()
    
    # Показване на резултатите
    print("📈 Резултати:")
    print("-" * 60)
    print(f"{'Локации':<10} {'Време':<10} {'Метод':<25} {'Статус'}")
    print("-" * 60)
    
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{result['size']:<10} {result['duration']:<10.2f} {result['method']:<25} {status}")
    
    print()
    print("🎯 Заключения:")
    
    # Анализ на ефективността
    fast_results = [r for r in results if r['success'] and r['duration'] < 5.0]
    slow_results = [r for r in results if r['success'] and r['duration'] >= 5.0]
    
    if fast_results:
        max_fast = max(r['size'] for r in fast_results)
        print(f"   • До {max_fast} локации: Бързо ({[r['duration'] for r in fast_results if r['size'] == max_fast][0]:.2f}s)")
    
    if slow_results:
        min_slow = min(r['size'] for r in slow_results)
        print(f"   • От {min_slow} локации нагоре: По-бавно (OSRM chunking)")
    
    approx_results = [r for r in results if r['method'] == "Приблизителни стойности"]
    if approx_results:
        avg_approx_time = sum(r['duration'] for r in approx_results) / len(approx_results)
        print(f"   • Приблизителни стойности: Средно {avg_approx_time:.2f}s за големи datasets")
    
    print()
    print("💡 Препоръки:")
    print("   • Системата автоматично избира най-ефективният метод")
    print("   • За > 50 локации се използват приблизителни стойности")
    print("   • Това е оптималното решение за 150-300+ клиента")
    
    client.close()

if __name__ == "__main__":
    test_efficiency() 