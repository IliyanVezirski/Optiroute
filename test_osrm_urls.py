"""
Тест за OSRM URL форматиране
"""

from osrm_client import OSRMClient
from config import get_config
import requests

def test_osrm_urls():
    """Тества различни OSRM URL формати"""
    
    print("🧪 Тестване на OSRM URL форматиране")
    print("=" * 50)
    
    config = get_config()
    client = OSRMClient(config.osrm)
    
    # Тестови локации от София, България
    depot = (42.695785029219415, 23.23165887245312)  # Депо
    center = (42.69769851709216, 23.32175896081278)  # Център
    test_locations = [depot, center]
    
    print(f"🏠 Депо: {depot}")
    print(f"🏢 Център: {center}")
    print()
    
    # Тест 1: URL форматиране
    print("1️⃣ Тестване на URL форматиране:")
    url = client._build_matrix_url(test_locations)
    print(f"   📍 Matrix URL: {url}")
    print()
    
    # Тест 2: Опит за заявка
    print("2️⃣ Тестване на Matrix API заявка:")
    try:
        # Първо тестваме само статуса на сървъра
        base_url = config.osrm.base_url.rstrip('/')
        status_response = requests.get(f"{base_url}/", timeout=5)
        print(f"   🟢 Сървър статус: {status_response.status_code}")
        
        # Тестваме table service 
        matrix = client.get_distance_matrix(test_locations)
        print(f"   ✅ Matrix успешен: {len(matrix.distances)}x{len(matrix.distances[0])}")
        print(f"   📏 Разстояние: {matrix.distances[0][1]:.0f} метра")
        print(f"   ⏱️ Време: {matrix.durations[0][1]:.0f} секунди")
        
    except Exception as e:
        print(f"   ❌ Грешка: {e}")
        
        # Тестваме route service като fallback
        print("\n3️⃣ Тестване на Route API като fallback:")
        try:
            lat1, lon1 = depot
            lat2, lon2 = center
            route_url = f"{base_url}/route/v1/driving/{lon1:.6f},{lat1:.6f};{lon2:.6f},{lat2:.6f}?overview=false&steps=false"
            print(f"   📍 Route URL: {route_url}")
            
            route_response = requests.get(route_url, timeout=10)
            print(f"   🌐 Route статус: {route_response.status_code}")
            
            if route_response.status_code == 200:
                data = route_response.json()
                if data['code'] == 'Ok' and data['routes']:
                    route = data['routes'][0]
                    print(f"   ✅ Route успешен: {route['distance']:.0f}м, {route['duration']:.0f}с")
                else:
                    print(f"   ❌ Route грешка: {data.get('message', 'Неизвестна')}")
            else:
                print(f"   ❌ HTTP грешка: {route_response.text}")
                
        except Exception as route_error:
            print(f"   ❌ Route грешка: {route_error}")
    
    print()
    print("🎯 Заключение:")
    print("   Ако видите 'Matrix успешен' - table service работи")
    print("   Ако видите 'Route успешен' - може да се използва route fallback")
    print("   Ако и двете дават грешки - проблем с OSRM конфигурацията")
    
    client.close()

if __name__ == "__main__":
    test_osrm_urls() 