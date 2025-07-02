"""
Тест скрипт за проверка на локален OSRM сървър
"""

import requests
import json
from config import get_config

def test_local_osrm_connection():
    """Тества връзката с локалния OSRM сървър"""
    config = get_config().osrm
    
    print(f"🔍 Тестване на връзка с локален OSRM сървър: {config.base_url}")
    print("-" * 60)
    
    try:
        # Тест на основния endpoint
        response = requests.get(config.base_url, timeout=5)
        print(f"📡 Отговор от {config.base_url}: код {response.status_code}")
        
        # Тест на различни endpoints
        endpoints = ["/health", ""]
        
        for endpoint in endpoints:
            try:
                url = f"{config.base_url}{endpoint}"
                resp = requests.get(url, timeout=5)
                print(f"📡 {url}: код {resp.status_code}")
                if resp.status_code == 200:
                    print("✅ Локален OSRM сървър е достъпен")
                    return True
            except:
                pass
        
        # Ако никой endpoint не върне 200, но има отговор
        if response.status_code in [400, 404]:
            print("✅ Локален OSRM сървър работи (очаква правилни заявки)")
            return True
        else:
            print(f"⚠️ Неочакван отговор от OSRM сървър")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Локален OSRM сървър не е достъпен")
        print("💡 Стартирайте OSRM сървър на localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Грешка при тестване на OSRM: {e}")
        return False

def test_local_osrm_matrix():
    """Тества matrix заявка към локалния OSRM сървър"""
    config = get_config().osrm
    
    print(f"\n🗺️ Тестване на matrix заявка")
    print("-" * 40)
    
    # Тест локации в София
    locations = [
        (42.6977, 23.3219),  # София център
        (42.7014, 23.3206),  # Близо до центъра
    ]
    
    # Построяване на URL
    coords_str = ';'.join([f"{lon},{lat}" for lat, lon in locations])
    url = f"{config.base_url}/table/v1/{config.profile}/{coords_str}"
    
    try:
        print(f"📡 Заявка: {url}")
        response = requests.get(url, timeout=config.timeout_seconds)
        
        print(f"📡 Статус код: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP грешка: {response.status_code}")
            print(f"📄 Отговор: {response.text[:200]}")
            return False
        
        data = response.json()
        print(f"📄 OSRM код: {data.get('code', 'Няма код')}")
        print(f"📄 Ключове: {list(data.keys())}")
        
        if data.get('code') == 'Ok':
            print("✅ Matrix заявка успешна!")
            
            if 'durations' in data:
                durations = data['durations']
                duration_min = durations[0][1] / 60
                
                # Ако има distances, използваме ги
                if 'distances' in data:
                    distances = data['distances']
                    distance_km = distances[0][1] / 1000
                    print(f"📏 Разстояние: {distance_km:.2f} км")
                else:
                    # Изчисляваме разстояние от времето
                    distance_km = (duration_min / 60) * config.average_speed_kmh
                    print(f"📏 Приблизително разстояние: {distance_km:.2f} км (от време)")
                
                print(f"⏱️ Време: {duration_min:.1f} минути")
                return True
            else:
                print(f"❌ Липсва durations в отговора")
                return False
        else:
            print(f"❌ OSRM грешка: {data.get('message', 'Неизвестна грешка')}")
            return False
            
    except Exception as e:
        print(f"❌ Грешка при matrix заявка: {e}")
        return False

def test_osrm_client():
    """Тества OSRM клиента на програмата"""
    print(f"\n🔧 Тестване на OSRM клиент")
    print("-" * 30)
    
    try:
        from osrm_client import OSRMClient
        
        client = OSRMClient()
        
        # Тест локации
        locations = [
            (42.6977, 23.3219),  # София център  
            (42.7014, 23.3206),  # Близо до центъра
        ]
        
        matrix = client.get_distance_matrix(locations)
        
        print("✅ OSRM клиент работи правилно")
        print(f"📏 Разстояние: {matrix.distances[0][1]/1000:.2f} км")
        print(f"⏱️ Време: {matrix.durations[0][1]/60:.1f} минути")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Грешка в OSRM клиент: {e}")
        return False

def test_fallback_functionality():
    """Тества fallback функционалността"""
    print(f"\n🔄 Тестване на fallback функционалност")
    print("-" * 45)
    
    try:
        from osrm_client import OSRMClient
        from config import OSRMConfig
        
        # Конфигурация с невалиден локален сървър и fallback
        test_config = OSRMConfig(
            base_url="http://localhost:9999",  # невалиден порт
            fallback_to_public=True,
            public_osrm_url="http://router.project-osrm.org",
            timeout_seconds=5,
            retry_attempts=1
        )
        
        client = OSRMClient(test_config)
        
        locations = [
            (42.6977, 23.3219),
            (42.7014, 23.3206)
        ]
        
        matrix = client.get_distance_matrix(locations)
        
        print("✅ Fallback функционалност работи")
        print("📡 Успешно превключване към публичен OSRM сървър")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Грешка при тестване на fallback: {e}")
        return False

def recommend_osrm_setup():
    """Дава препоръки за настройка на OSRM"""
    print(f"\n💡 ПРЕПОРЪКИ ЗА НАСТРОЙКА НА ЛОКАЛЕН OSRM:")
    print("=" * 50)
    
    print("1. Инсталиране с Docker:")
    print("   docker pull osrm/osrm-backend")
    print()
    
    print("2. Изтегляне на България OSM данни:")
    print("   wget https://download.geofabrik.de/europe/bulgaria-latest.osm.pbf")
    print()
    
    print("3. Обработка на данните:")
    print("   docker run -t -v \"${PWD}:/data\" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/bulgaria-latest.osm.pbf")
    print("   docker run -t -v \"${PWD}:/data\" osrm/osrm-backend osrm-partition /data/bulgaria-latest.osrm")
    print("   docker run -t -v \"${PWD}:/data\" osrm/osrm-backend osrm-customize /data/bulgaria-latest.osrm")
    print()
    
    print("4. Стартиране на сървъра:")
    print("   docker run -t -i -p 5000:5000 -v \"${PWD}:/data\" osrm/osrm-backend osrm-routed --algorithm mld /data/bulgaria-latest.osrm")
    print()
    
    print("5. Тестване:")
    print("   curl \"http://localhost:5000/health\"")

def main():
    """Стартира всички тестове"""
    print("🧪 ТЕСТВАНЕ НА ЛОКАЛЕН OSRM СЪРВЪР")
    print("=" * 60)
    
    tests = [
        ("Връзка с локален OSRM", test_local_osrm_connection),
        ("Matrix заявка", test_local_osrm_matrix)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔹 Тест: {test_name}")
        if test_func():
            passed += 1
    
    print(f"\n📊 РЕЗУЛТАТИ: {passed}/{total} тестове преминаха")
    
    if passed == 0:
        print("\n⚠️ Локален OSRM сървър не е настроен.")
        print("💡 Следвайте инструкциите в README.md за настройка на OSRM")
    elif passed < total:
        print(f"\n⚠️ {total - passed} теста не преминаха.")
    else:
        print("\n🎉 Локален OSRM сървър работи отлично!")

if __name__ == "__main__":
    main() 