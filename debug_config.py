#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def debug_config_file():
    """Дебъг на config.py файла"""
    try:
        with open('config.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"Total lines in config.py: {len(lines)}")
        
        # Търсим всички OSRMConfig класове
        osrm_classes = []
        for i, line in enumerate(lines):
            if 'class OSRMConfig' in line:
                osrm_classes.append(i + 1)  # 1-based line numbers
        
        print(f"OSRMConfig classes found at lines: {osrm_classes}")
        
        # Търсим chunk_size дефиниции
        chunk_sizes = []
        for i, line in enumerate(lines):
            if 'chunk_size:' in line and '=' in line:
                chunk_sizes.append((i + 1, line.strip()))
        
        print(f"chunk_size definitions:")
        for line_num, content in chunk_sizes:
            print(f"  Line {line_num}: {content}")
        
        # Проверяваме дали файлът е дублиран
        midpoint = len(lines) // 2
        first_half = lines[:midpoint]
        second_half = lines[midpoint:]
        
        if len(first_half) == len(second_half):
            identical_lines = sum(1 for a, b in zip(first_half, second_half) if a == b)
            if identical_lines > midpoint * 0.8:  # 80%+ identical
                print(f"⚠️  FILE IS DUPLICATED! {identical_lines}/{midpoint} lines are identical")
            else:
                print(f"File halves are different ({identical_lines}/{midpoint} identical)")
        
        # Опитваме се да import-нем
        print("\nTrying to import OSRMConfig...")
        from config import OSRMConfig
        osrm = OSRMConfig()
        print(f"Successfully imported. chunk_size = {osrm.chunk_size}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_config_file() 