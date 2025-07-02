"""
Скрипт за създаване на примерни тестови данни за CVRP програмата
"""

import pandas as pd
import random
import os

def create_sample_excel():
    """Създава примерен Excel файл с клиентски данни"""
    
    # Базови координати за София и околностите
    base_lat = 42.6977
    base_lon = 23.3219
    
    # Генерираме примерни клиенти
    clients_data = []
    
    for i in range(1, 26):  # 25 клиента
        # Генерираме GPS координати около София
        lat_offset = random.uniform(-0.1, 0.1)  # ±10км приблизително
        lon_offset = random.uniform(-0.1, 0.1)
        
        lat = base_lat + lat_offset
        lon = base_lon + lon_offset
        
        # Генерираме различни формати на GPS данни
        gps_formats = [
            f"{lat:.6f}, {lon:.6f}",
            f"{lat:.6f},{lon:.6f}",
            f"{lat:.5f} {lon:.5f}",
            f"N{lat:.5f} E{lon:.5f}"
        ]
        
        gps_data = random.choice(gps_formats)
        
        # Генерираме обем (стотинки)
        volume = random.randint(10, 150)
        
        clients_data.append({
            'Клиент': f'K{i:03d}',
            'Име клиент': f'Клиент {i}',
            'Gpsdata': gps_data,
            'Обем': volume
        })
    
    # Създаваме DataFrame
    df = pd.DataFrame(clients_data)
    
    # Записваме в Excel файл
    output_file = 'data/sample_clients.xlsx'
    os.makedirs('data', exist_ok=True)
    
    df.to_excel(output_file, index=False, engine='openpyxl')
    
    print(f"✅ Създаден примерен Excel файл: {output_file}")
    print(f"📊 Брой клиенти: {len(clients_data)}")
    print(f"📦 Общ обем: {df['Обем'].sum()} стотинки")
    print(f"📍 GPS формати: {len(set([type(gps) for gps in df['Gpsdata']]))}")
    
    # Показваме първите 5 реда
    print("\n📋 Първи 5 реда:")
    print(df.head().to_string(index=False))
    
    return output_file

if __name__ == "__main__":
    create_sample_excel() 