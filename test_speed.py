#!/usr/bin/env python3
"""
Тест на скоростта на новия оптимизиран OSRM подход
"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from osrm_client import create_osrm_client

def test_speed_optimization():
    """Тества скоростта на оптимизирания подход"""
    
    print("🚀 ТЕСТ НА СКОРОСТТА НА OSRM ОПТИМИЗАЦИИТЕ")
    print("=" * 60)
    
    client = create_osrm_client()
    
    # Тест 1: Малки данни (10 локации = 90 заявки)
    print("1️⃣ ТЕСТ: 10 локации (90 заявки)")
    locations_10 = [
        (42.6977, 23.3219),  # София център
        (42.7001, 23.3240),  # близо до центъра
        (42.6950, 23.3190),  # южно от центъра
        (42.7020, 23.3280),  # северно от центъра
        (42.6930, 23.3160),  # югозападно
        (42.6980, 23.3300),  # североизточно
        (42.6920, 23.3130),  # югозападно 2
        (42.7040, 23.3200),  # северозападно
        (42.6900, 23.3250),  # южно 2
        (42.7000, 23.3150)   # централно 2
    ]
    
    start_time = time.time()
    matrix_10 = client.get_distance_matrix(locations_10)
    duration_10 = time.time() - start_time
    speed_10 = 90 / duration_10  # заявки/сек
    
    print(f"✅ 10 локации завърши за {duration_10:.2f}s")
    print(f"⚡ Скорост: {speed_10:.1f} заявки/сек")
    print(f"📊 Реални данни: {matrix_10.distances[0][1]:.0f}м")
    print()
    
    # Тест 2: Средни данни (20 локации = 380 заявки) 
    print("2️⃣ ТЕСТ: 20 локации (380 заявки)")
    locations_20 = locations_10 + [
        (42.6960, 23.3320),
        (42.6940, 23.3110),
        (42.7060, 23.3180),
        (42.6880, 23.3270),
        (42.7020, 23.3130),
        (42.6990, 23.3340),
        (42.6910, 23.3090),
        (42.7080, 23.3160),
        (42.6860, 23.3290),
        (42.7040, 23.3110)
    ]
    
    start_time = time.time()
    matrix_20 = client.get_distance_matrix(locations_20)
    duration_20 = time.time() - start_time
    speed_20 = 380 / duration_20  # заявки/сек
    
    print(f"✅ 20 локации завърши за {duration_20:.2f}s")
    print(f"⚡ Скорост: {speed_20:.1f} заявки/сек")
    print(f"📊 Реални данни: {matrix_20.distances[0][5]:.0f}м")
    print()
    
    # Прогноза за 273 локации
    estimated_requests_273 = 273 * 272  # 74,256 заявки
    estimated_time_273 = estimated_requests_273 / speed_20 / 60  # в минути
    
    print("📈 РЕЗУЛТАТИ И ПРОГНОЗИ:")
    print(f"   🔢 10 локации: {speed_10:.1f} заявки/сек")
    print(f"   🔢 20 локации: {speed_20:.1f} заявки/сек") 
    print(f"   📊 Средна скорост: {(speed_10 + speed_20)/2:.1f} заявки/сек")
    print()
    print(f"🎯 ПРОГНОЗА ЗА 273 ЛОКАЦИИ:")
    print(f"   📊 Общо заявки: {estimated_requests_273:,}")
    print(f"   ⏱️ Очаквано време: {estimated_time_273:.1f} минути")
    
    # Сравнение с предишната версия
    old_speed = 25  # заявки/сек от предишния тест
    improvement = speed_20 / old_speed
    old_time_273 = estimated_requests_273 / old_speed / 60
    
    print()
    print(f"🚀 ПОДОБРЕНИЕ СПРЯМО СТАРИЯ ПОДХОД:")
    print(f"   📈 Ускорение: {improvement:.1f}x по-бърз")
    print(f"   ⏰ Стар подход: {old_time_273:.1f} минути")
    print(f"   ⚡ Нов подход: {estimated_time_273:.1f} минути")
    print(f"   💾 Спестено време: {old_time_273 - estimated_time_273:.1f} минути")
    
    client.close()

if __name__ == "__main__":
    test_speed_optimization() 