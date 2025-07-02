"""
Тест за OSRM Route API функциите в output_handler
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from output_handler import InteractiveMapGenerator
from config import get_config
import logging

# Настройваме logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_osrm_route_geometry():
    """Тества OSRM Route API геометрия"""
    print("🧪 Тествам OSRM Route API геометрия...")
    
    # Създаваме map generator
    config = get_config().output
    map_generator = InteractiveMapGenerator(config)
    
    # Тестови координати (София)
    start_coords = (42.697735, 23.321589)  # Център
    end_coords = (42.695785, 23.231659)    # Депо
    
    print(f"📍 От: {start_coords}")
    print(f"📍 До: {end_coords}")
    
    # Тестваме единичен сегмент
    print("\n1️⃣ Тествам единичен сегмент...")
    geometry = map_generator._get_osrm_route_geometry(start_coords, end_coords)
    print(f"   Резултат: {len(geometry)} точки")
    print(f"   Първа точка: {geometry[0]}")
    print(f"   Последна точка: {geometry[-1]}")
    
    # Тестваме пълен маршрут
    print("\n2️⃣ Тествам пълен маршрут...")
    waypoints = [
        (42.697735, 23.321589),  # Център
        (42.7, 23.3),            # Клиент 1
        (42.71, 23.31),          # Клиент 2
        (42.695785, 23.231659)   # Депо
    ]
    
    full_geometry = map_generator._get_full_route_geometry(waypoints)
    print(f"   Резултат: {len(full_geometry)} точки")
    print(f"   Първа точка: {full_geometry[0]}")
    print(f"   Последна точка: {full_geometry[-1]}")
    
    print("\n✅ Тестът завърши успешно!")

def test_osrm_connectivity():
    """Тества OSRM connectivity"""
    print("🔗 Тествам OSRM connectivity...")
    
    try:
        import requests
        from config import get_config
        
        osrm_config = get_config().osrm
        test_url = f"{osrm_config.base_url.rstrip('/')}/route/v1/driving/23.3,42.7;23.3,42.7"
        
        print(f"   URL: {test_url}")
        
        response = requests.get(test_url, timeout=5)
        print(f"   Статус код: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   OSRM отговор: {data.get('code', 'Unknown')}")
            print("   ✅ OSRM сървърът работи!")
        else:
            print("   ❌ OSRM сървърът не отговаря правилно")
            
    except Exception as e:
        print(f"   ❌ Грешка при свързване: {e}")

if __name__ == "__main__":
    print("🚀 Стартирам тестове за OSRM Route API...\n")
    
    # Тест 1: Connectivity
    test_osrm_connectivity()
    print()
    
    # Тест 2: Route geometry
    test_osrm_route_geometry()
    
    print("\n🎉 Всички тестове завършиха!") 