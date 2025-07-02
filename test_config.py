#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config import MainConfig

def test_osrm_limits():
    """Показва актуалните OSRM лимити и настройки"""
    config = MainConfig()
    
    print("🌐 OSRM Настройки:")
    print(f"   📊 Chunk size: {config.osrm.chunk_size}")
    print(f"   ⏱️ Timeout: {config.osrm.timeout_seconds}s")
    print(f"   🔄 Retry attempts: {config.osrm.retry_attempts}")
    print(f"   🚀 Average speed: {config.osrm.average_speed_kmh} km/h")
    print()
    
    # Пресмятане за различни броя клиенти
    test_clients = [50, 100, 150, 250, 500]
    
    print("📈 Chunks за различни броя клиенти:")
    for clients in test_clients:
        chunks_per_side = (clients + config.osrm.chunk_size - 1) // config.osrm.chunk_size
        total_chunks = chunks_per_side * chunks_per_side
        print(f"   {clients:3d} клиента: {total_chunks:2d} chunks")
    
    print()
    print("⚡ Лимити:")
    print("   • Локален OSRM: ~100 локации per chunk (препоръчително)")
    print("   • Публичен OSRM GET: ~25 локации per chunk")
    print("   • Публичен OSRM POST: ~100 локации per chunk")
    print("   • Route API: 1 заявка = 1 маршрут (МНОГО БАВНО за >15 локации)")

if __name__ == "__main__":
    test_osrm_limits() 