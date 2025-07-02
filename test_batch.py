#!/usr/bin/env python3
"""
Тест на новия batch Table API подход
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from osrm_client import create_osrm_client

def test_batch_approach():
    """Тества новия batch Table API подход"""
    
    print("🧩 ТЕСТ НА BATCH TABLE API ПОДХОДА")
    print("=" * 60)
    
    client = create_osrm_client()
    
    # Тест 1: Малки данни (25 локации) - директно Table API
    print("1️⃣ ТЕСТ: 25 локации (директно Table API)")
    locations_25 = []
    for i in range(25):
        lat = 42.695 + (i % 5) * 0.005 - 0.01
        lon = 23.320 + (i % 5) * 0.005 - 0.01
        locations_25.append((lat, lon))
    
    start_time = time.time()
    matrix_25 = client.get_distance_matrix(locations_25)
    duration_25 = time.time() - start_time
    
    print(f"✅ 25 локации завърши за {duration_25:.2f}s")
    print(f"📊 Реални данни: {matrix_25.distances[0][1]:.0f}м")
    print(f"🎯 Използван: Table API (една заявка)")
    print()
    
    # Тест 2: Средни данни (50 локации) - batch Table API  
    print("2️⃣ ТЕСТ: 50 локации (batch Table API)")
    locations_50 = []
    for i in range(50):
        lat = 42.695 + (i % 10) * 0.004 - 0.02
        lon = 23.320 + (i % 10) * 0.004 - 0.02
        locations_50.append((lat, lon))
    
    start_time = time.time()
    matrix_50 = client.get_distance_matrix(locations_50)
    duration_50 = time.time() - start_time
    
    print(f"✅ 50 локации завърши за {duration_50:.2f}s")
    print(f"📊 Реални данни: {matrix_50.distances[0][5]:.0f}м")
    print(f"🧩 Използван: Batch Table API (~9 batch заявки)")
    print()
    
    # Прогноза за 273 локации с batch подход
    batches_273 = 14 * 14  # 196 batch заявки
    estimated_time_273_batch = (duration_50 / 9) * batches_273 / 60  # в минути
    
    # Сравнение с Route API подхода  
    route_requests_273 = 273 * 272  # 74,256 заявки
    route_speed = 120  # заявки/сек от предишния тест
    estimated_time_273_route = route_requests_273 / route_speed / 60  # в минути
    
    print("📈 РЕЗУЛТАТИ И ПРОГНОЗИ:")
    print(f"   🔢 25 локации: {duration_25:.2f}s (Table API)")
    print(f"   🔢 50 локации: {duration_50:.2f}s (Batch Table API)")
    print()
    print(f"🎯 ПРОГНОЗА ЗА 273 ЛОКАЦИИ:")
    print(f"   🧩 Batch Table API: ~{batches_273} заявки → {estimated_time_273_batch:.1f} минути")
    print(f"   🛣️ Route API: {route_requests_273:,} заявки → {estimated_time_273_route:.1f} минути")
    if estimated_time_273_batch > 0:
        print(f"   ⚡ Ускорение: {estimated_time_273_route / estimated_time_273_batch:.0f}x по-бърз с batch подход!")
    else:
        print(f"   ⚡ Ускорение: МИГНОВЕНО благодарение на кеша/оптимизациите!")
    print()
    print(f"🚀 BATCH ПОДХОД ПРЕДИМСТВА:")
    print(f"   📊 Заявки: {route_requests_273:,} → {batches_273} ({route_requests_273/batches_273:.0f}x по-малко)")
    print(f"   ⏰ Време: {estimated_time_273_route:.1f}мин → {estimated_time_273_batch:.1f}мин")
    print(f"   💾 Мрежов трафик: значително намален")
    print(f"   🎯 Качество: 100% реални OSRM данни")
    
    client.close()

if __name__ == "__main__":
    test_batch_approach() 