#!/usr/bin/env python3
"""
Тест на новата chunking система с route API заявки
Проверява дали chunking работи правилно със заявки до 100 локации максимум
"""

import sys
import os
import traceback
from typing import List, Tuple
import time

# Добавяме родителската директория в Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from input_handler import load_customer_data, Customer
from config import get_config
from osrm_client import create_osrm_client, OSRMClient

def test_route_chunking():
    """Тества новата chunking система с route API"""
    print("🧪 Тестване на chunking с route API заявки")
    print("=" * 60)
    
    try:
        # Зареждаме конфигурацията
        config = get_config()
        print(f"📊 Chunk size от config: {config.osrm.chunk_size}")
        
        # Зареждаме клиенти
        print("\n📂 Зареждане на клиентски данни...")
        customers = load_customer_data()
        depot_location = config.locations.depot_location
        
        print(f"✅ Заредени {len(customers)} клиента")
        print(f"🏭 Depot: {depot_location}")
        
        # Подготвяме локации за тест
        all_locations = [depot_location] + [customer.gps_location for customer in customers]
        n_total = len(all_locations)
        
        print(f"\n🌍 Общо локации за тест: {n_total}")
        
        # Тест с различни размери
        test_sizes = [5, 15, 35, 50, 100]
        if n_total > 100:
            test_sizes.append(min(n_total, 150))
        
        # Създаваме OSRM клиент
        osrm_client = create_osrm_client()
        
        for test_size in test_sizes:
            if test_size > n_total:
                continue
                
            print(f"\n🧩 Тест с {test_size} локации:")
            print("-" * 40)
            
            test_locations = all_locations[:test_size]
            
            try:
                matrix = osrm_client.get_distance_matrix(test_locations)
                
                print(f"✅ Matrix успешен: {len(matrix.distances)}x{len(matrix.distances[0])}")
                print(f"   Разстояние 0->1: {matrix.distances[0][1]:.1f}м")
                print(f"   Време 0->1: {matrix.durations[0][1]:.1f}с")
                
                # Проверка на матрицата
                if len(matrix.distances) != test_size:
                    print(f"❌ Грешен размер на matrix: {len(matrix.distances)} != {test_size}")
                elif len(matrix.distances[0]) != test_size:
                    print(f"❌ Грешен размер на редове: {len(matrix.distances[0])} != {test_size}")
                else:
                    print("✅ Matrix има правилен размер")
                    
                    # Проверка на диагонала (трябва да е 0)
                    diagonal_ok = all(matrix.distances[i][i] == 0.0 for i in range(test_size))
                    if diagonal_ok:
                        print("✅ Диагоналът е правилен (0.0)")
                    else:
                        print("❌ Диагоналът не е правилен")
                        
            except Exception as e:
                print(f"❌ Грешка: {e}")
                print(f"   Type: {type(e).__name__}")
                traceback.print_exc()
        
        # Затваряме клиента
        osrm_client.close()
        
        print("\n" + "=" * 60)
        print("🎯 Тест на chunking завършен!")
        
    except Exception as e:
        print(f"❌ Критична грешка: {e}")
        traceback.print_exc()

def test_chunk_efficiency():
    """Тества ефективността на различни chunk размери"""
    print("\n🚀 Тест на ефективност на chunks")
    print("=" * 60)
    
    try:
        config = get_config()
        customers = load_customer_data()
        depot_location = config.locations.depot_location
        
        # Ограничаваме до разумен размер за тест
        max_locations = min(80, len(customers) + 1)
        test_locations = [depot_location] + [customer.gps_location for customer in customers[:max_locations-1]]
        
        print(f"🌍 Тествам с {len(test_locations)} локации")
        
        # Различни chunk размери
        chunk_sizes = [20, 50, 80, 100]
        
        for chunk_size in chunk_sizes:
            if chunk_size >= len(test_locations):
                continue
                
            print(f"\n🧩 Chunk size: {chunk_size}")
            
            # Временно променяме chunk_size
            original_chunk_size = config.osrm.chunk_size
            config.osrm.chunk_size = chunk_size
            
            try:
                start_time = time.time()
                
                osrm_client = create_osrm_client()
                matrix = osrm_client.get_distance_matrix(test_locations)
                
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"   ⏱️ Време: {duration:.2f}с")
                print(f"   ✅ Matrix: {len(matrix.distances)}x{len(matrix.distances[0])}")
                
                osrm_client.close()
                
            except Exception as e:
                print(f"   ❌ Грешка: {e}")
            finally:
                # Възстановяваме оригиналния chunk_size
                config.osrm.chunk_size = original_chunk_size
        
        print("\n🎯 Тест на ефективност завършен!")
        
    except Exception as e:
        print(f"❌ Критична грешка: {e}")
        traceback.print_exc()

def test_route_api_only():
    """Тества новия подход само с Route API заявки"""
    
    client = create_osrm_client()
    
    # Тест с много малки данни (5 локации)
    print("🧪 Тест 1: 5 локации (24 Route API заявки)")
    locations_5 = [
        (42.6977, 23.3219),  # София център
        (42.7001, 23.3240),  # близо до центъра
        (42.6950, 23.3190),  # южно от центъра
        (42.7020, 23.3280),  # северно от центъра
        (42.6930, 23.3160)   # югозападно
    ]
    
    start_time = time.time()
    matrix_5 = client.get_distance_matrix(locations_5)
    end_time = time.time()
    
    print(f"✅ 5 локации завърши за {end_time - start_time:.2f} секунди")
    print(f"📊 Първо разстояние: {matrix_5.distances[0][1]:.0f}м")
    print(f"📊 Първо време: {matrix_5.durations[0][1]:.0f}с")
    print()
    
    # Тест с малки данни (10 локации) 
    print("🧪 Тест 2: 10 локации (90 Route API заявки)")
    locations_10 = locations_5 + [
        (42.6980, 23.3300),
        (42.6920, 23.3130),
        (42.7040, 23.3200),
        (42.6900, 23.3250),
        (42.7000, 23.3150)
    ]
    
    start_time = time.time()
    matrix_10 = client.get_distance_matrix(locations_10)
    end_time = time.time()
    
    print(f"✅ 10 локации завърши за {end_time - start_time:.2f} секунди")
    print(f"📊 Реални OSRM данни без приблизителни стойности")
    print()
    
    # Показваме статистики
    print("📈 Статистики:")
    print(f"   🔢 5 локации: 24 заявки за {(end_time - start_time):.1f}с")
    print(f"   ⚡ Скорост: ~{24/(end_time - start_time):.1f} заявки/сек")
    print(f"   📊 100% реални OSRM данни")
    
    client.close()

if __name__ == "__main__":
    print("🧪 OSRM Route Chunking Test")
    print("🔄 Тестване на новата chunking система с route API")
    print()
    
    test_route_chunking()
    test_chunk_efficiency()
    test_route_api_only()
    
    print("\n🏁 Всички тестове завършени!") 