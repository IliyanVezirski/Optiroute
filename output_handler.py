"""
Модул за обработка на изходни данни
Създава интерактивна карта, Excel файлове и чартове за анализ
"""

import folium
import pandas as pd
import requests
import json
from typing import List, Dict, Tuple, Optional
import os
import logging
from config import get_config, OutputConfig
from cvrp_solver import CVRPSolution, Route
from warehouse_manager import WarehouseAllocation
from input_handler import Customer
from osrm_client import get_distance_matrix_from_central_cache

logger = logging.getLogger(__name__)

# Настройки за различните типове превозни средства
VEHICLE_SETTINGS = {
    'internal_bus': {
        'color': 'blue',
        'icon': 'bus',
        'prefix': 'fa',
        'name': 'Вътрешен автобус'
    },
    'center_bus': {
        'color': 'red', 
        'icon': 'building',
        'prefix': 'fa',
        'name': 'Централен автобус'
    },
    'external_bus': {
        'color': 'green',
        'icon': 'truck',
        'prefix': 'fa', 
        'name': 'Външен автобус'
    }
}

# Цветове за всеки отделен автобус
BUS_COLORS = [
    '#FF0000',  # Червен
    '#00FF00',  # Зелен  
    '#0000FF',  # Син
    '#FFFF00',  # Жълт
    '#FF00FF',  # Магента
    '#00FFFF',  # Циан
    '#FFA500',  # Оранжев
    '#800080',  # Лилав
    '#008000',  # Тъмно зелен
    '#000080',  # Тъмно син
    '#800000',  # Бордо
    '#808000',  # Маслинен
    '#FF69B4',  # Розов
    '#32CD32',  # Лайм зелен
    '#8A2BE2',  # Синьо виолетов
    '#FF4500',  # Червено оранжев
    '#2E8B57',  # Морско зелен
    '#4682B4',  # Стоманено син
    '#D2691E',  # Шоколадов
    '#DC143C'   # Тъмно червен
]


class InteractiveMapGenerator:
    """Генератор на интерактивна карта"""
    
    def __init__(self, config: OutputConfig):
        self.config = config
        # Зареждаме централната матрица
        self.central_matrix = get_distance_matrix_from_central_cache([])
        self.use_osrm_routing = self.central_matrix is not None
        if not self.central_matrix:
            logger.warning("❌ Не можах да заредя централната матрица. Ще използвам прави линии.")
    
    def create_map(self, solution: CVRPSolution, warehouse_allocation: WarehouseAllocation,
                  depot_location: Tuple[float, float]) -> folium.Map:
        """Създава интерактивна карта с маршрутите"""
        logger.info("Създавам интерактивна карта")
        
        # Инициализация на картата
        route_map = folium.Map(
            location=depot_location,
            zoom_start=self.config.map_zoom_level,
            tiles='OpenStreetMap'
        )
        
        # Добавяне на депото
        self._add_depot_marker(route_map, depot_location)
        
        # Добавяне на маршрутите с OSRM геометрия
        if self.config.show_route_colors:
            self._add_routes_to_map(route_map, solution.routes, depot_location)
        
        # Добавяне на легенда
        self._add_legend(route_map, solution.routes)
        
        return route_map
    
    def _add_depot_marker(self, route_map: folium.Map, depot_location: Tuple[float, float]):
        """Добавя маркер за депото"""
        folium.Marker(
            depot_location,
            popup="<b>Депо/Стартова точка</b>",
            tooltip="Депо",
            icon=folium.Icon(color='black', icon='home', prefix='fa')
        ).add_to(route_map)
    
    def _get_osrm_route_geometry(self, start_coords: Tuple[float, float], 
                                end_coords: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Получава реална геометрия на маршрута от централната матрица"""
        # Ако нямаме централна матрица, връщаме права линия
        if not self.central_matrix:
            return [start_coords, end_coords]
            
        try:
            # Търсим индексите на точките в централната матрица
            start_idx = -1
            end_idx = -1
            for idx, loc in enumerate(self.central_matrix.locations):
                if abs(loc[0] - start_coords[0]) < 0.0001 and abs(loc[1] - start_coords[1]) < 0.0001:
                    start_idx = idx
                if abs(loc[0] - end_coords[0]) < 0.0001 and abs(loc[1] - end_coords[1]) < 0.0001:
                    end_idx = idx
                if start_idx >= 0 and end_idx >= 0:
                    break
            
            # Ако не намерим точките, връщаме права линия
            if start_idx == -1 or end_idx == -1:
                logger.debug(f"Точките не са намерени в централната матрица: {start_coords} -> {end_coords}")
                return [start_coords, end_coords]
            
            # Връщаме точките от матрицата
            return [start_coords, end_coords]
            
        except Exception as e:
            logger.warning(f"Грешка при използване на централната матрица: {e}")
            return [start_coords, end_coords]
    
    def _get_full_route_geometry(self, waypoints: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Получава пълната геометрия за маршрут с множество точки"""
        if len(waypoints) < 2:
            return waypoints
        
        # Връщаме последователност от точки
        full_geometry = []
        for i in range(len(waypoints) - 1):
            segment = self._get_osrm_route_geometry(waypoints[i], waypoints[i + 1])
            if i == 0:
                full_geometry.extend(segment)
            else:
                full_geometry.extend(segment[1:])  # Пропускаме дублираната точка
        
        return full_geometry if full_geometry else waypoints
    
    def _add_routes_to_map(self, route_map: folium.Map, routes: List[Route], depot_location: Tuple[float, float]):
        """Добавя маршрутите на картата с OSRM геометрия"""
        for route_idx, route in enumerate(routes):
            vehicle_settings = VEHICLE_SETTINGS.get(route.vehicle_type.value, {
                'color': 'gray', 
                'icon': 'circle',
                'prefix': 'fa',
                'name': 'Неизвестен'
            })
            
            # Всеки автобус получава уникален цвят
            bus_color = BUS_COLORS[route_idx % len(BUS_COLORS)]
            
            # Добавяне на клиентските маркери с номерация
            for client_idx, customer in enumerate(route.customers):
                if customer.coordinates:
                    # Създаваме номериран маркер
                    client_number = client_idx + 1
                    
                    # HTML за номерирано пинче с уникален цвят на автобуса
                    icon_html = f'''
                    <div style="
                        background-color: {bus_color};
                        border: 3px solid white;
                        border-radius: 50%;
                        width: 30px;
                        height: 30px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        font-weight: bold;
                        font-size: 14px;
                        color: white;
                        text-shadow: 1px 1px 1px rgba(0,0,0,0.7);
                    ">{client_number}</div>
                    '''
                    
                    popup_text = f"""
                    <div style="font-family: Arial, sans-serif;">
                        <h4 style="margin: 0; color: {bus_color};">
                            Автобус {route_idx + 1} - {vehicle_settings['name']}
                        </h4>
                        <hr style="margin: 5px 0;">
                        <b>Клиент:</b> {customer.name}<br>
                        <b>ID:</b> {customer.id}<br>
                        <b>Ред в маршрута:</b> #{client_number}<br>
                        <b>Обем:</b> {customer.volume:.2f} ст.<br>
                        <b>Координати:</b> {customer.coordinates[0]:.6f}, {customer.coordinates[1]:.6f}
                    </div>
                    """
                    
                    # Добавяме номерирания маркер
                    folium.Marker(
                        customer.coordinates,
                        popup=folium.Popup(popup_text, max_width=300),
                        tooltip=f"#{client_number}: {customer.name}",
                        icon=folium.DivIcon(
                            html=icon_html,
                            icon_size=(30, 30),
                            icon_anchor=(15, 15),
                            popup_anchor=(0, -15)
                        )
                    ).add_to(route_map)
            
            # Създаваме пълния маршрут: депо -> клиенти -> депо
            if route.customers and self.use_osrm_routing:
                logger.info(f"🛣️ Получавам OSRM маршрут за Автобус {route_idx + 1} с {len(route.customers)} клиента")
                
                # Подготвяме всички waypoints
                waypoints = [depot_location]
                for customer in route.customers:
                    if customer.coordinates:
                        waypoints.append(customer.coordinates)
                waypoints.append(depot_location)  # Връщане в депото
                
                # Получаваме реалната геометрия от OSRM
                try:
                    route_geometry = self._get_full_route_geometry(waypoints)
                    
                    if len(route_geometry) > 2:
                        folium.PolyLine(
                            route_geometry,
                            color=bus_color,
                            weight=4,
                            opacity=0.8,
                            popup=f"🚌 Автобус {route_idx + 1} - {vehicle_settings['name']} (OSRM маршрут)"
                        ).add_to(route_map)
                        logger.info(f"✅ OSRM маршрут добавен за Автобус {route_idx + 1}: {len(route_geometry)} точки")
                    else:
                        # Fallback към прави линии
                        folium.PolyLine(
                            waypoints,
                            color=bus_color,
                            weight=3,
                            opacity=0.6,
                            popup=f"🚌 Автобус {route_idx + 1} - {vehicle_settings['name']} (Прави линии)",
                            dashArray='5, 5'  # Пунктирана линия за показване че не е OSRM
                        ).add_to(route_map)
                        logger.warning(f"⚠️ Използвам прави линии за Автобус {route_idx + 1}")
                        
                except Exception as e:
                    logger.error(f"❌ Грешка при OSRM маршрут за Автобус {route_idx + 1}: {e}")
                    # Fallback към прави линии
                    waypoints = [depot_location]
                    for customer in route.customers:
                        if customer.coordinates:
                            waypoints.append(customer.coordinates)
                    waypoints.append(depot_location)
                    
                    folium.PolyLine(
                        waypoints,
                        color=bus_color,
                        weight=3,
                        opacity=0.6,
                        popup=f"🚌 Автобус {route_idx + 1} - {vehicle_settings['name']} (Fallback)",
                        dashArray='5, 5'
                    ).add_to(route_map)
            
            elif route.customers:
                # Fallback към прави линии ако OSRM е изключен
                waypoints = [depot_location]
                for customer in route.customers:
                    if customer.coordinates:
                        waypoints.append(customer.coordinates)
                waypoints.append(depot_location)
                
                folium.PolyLine(
                    waypoints,
                    color=bus_color,
                    weight=3,
                    opacity=0.8,
                    popup=f"🚌 Автобус {route_idx + 1} - {vehicle_settings['name']}"
                ).add_to(route_map)
    
    def _add_legend(self, route_map: folium.Map, routes: List[Route]):
        """Добавя легенда на картата"""
        legend_html = '''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 220px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px; border-radius: 5px;
                    box-shadow: 0 0 15px rgba(0,0,0,0.2);">
        <h4 style="margin-top:0; margin-bottom:10px; text-align: center;">Легенда</h4>
        '''
        
        # Добавяме депо
        legend_html += '''
        <p style="margin: 5px 0;">
            <i class="fa fa-home" style="color: black; margin-right: 8px;"></i>
            Депо
        </p>
        '''
        
        # Добавяме всеки автобус поотделно с уникалният му цвят
        for route_idx, route in enumerate(routes):
            vehicle_settings = VEHICLE_SETTINGS.get(route.vehicle_type.value, {
                'color': 'gray',
                'icon': 'circle', 
                'name': 'Неизвестен'
            })
            bus_color = BUS_COLORS[route_idx % len(BUS_COLORS)]
            client_count = len(route.customers)
            
            legend_html += f'''
            <p style="margin: 5px 0;">
                <span style="
                    display: inline-block;
                    background-color: {bus_color};
                    border: 2px solid white;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    margin-right: 8px;
                    vertical-align: middle;
                "></span>
                Автобус {route_idx + 1} ({client_count} клиента)
            </p>
            '''
        
        # Добавяме информация за OSRM маршрутите
        osrm_info = "🛣️ OSRM маршрути" if self.use_osrm_routing else "📐 Прави линии"
        
        legend_html += f'''
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0; font-size: 12px; color: #666;">
            Числата показват реда на посещение<br>
            {osrm_info}
        </p>
        </div>
        '''
        
        # Добавяме легендата към картата
        legend_element = folium.Element(legend_html)
        route_map.get_root().add_child(legend_element)
    
    def save_map(self, route_map: folium.Map, file_path: Optional[str] = None) -> str:
        """Записва картата във файл"""
        file_path = file_path or self.config.map_output_file
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        route_map.save(file_path)
        
        logger.info(f"Интерактивна карта записана в {file_path}")
        return file_path


class ExcelExporter:
    """Експортър на Excel файлове"""
    
    def __init__(self, config: OutputConfig):
        self.config = config
    
    def export_warehouse_orders(self, warehouse_customers: List[Customer]) -> str:
        """Експортира заявките в склада"""
        if not warehouse_customers:
            logger.info("Няма заявки за експорт в склада")
            return ""
        
        file_path = os.path.join(self.config.excel_output_dir, self.config.warehouse_excel_file)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        data = []
        for customer in warehouse_customers:
            data.append({
                'ID': customer.id,
                'Име': customer.name,
                'Обем (ст.)': customer.volume,
                'GPS координати': customer.original_gps_data,
                'Latitude': customer.coordinates[0] if customer.coordinates else '',
                'Longitude': customer.coordinates[1] if customer.coordinates else ''
            })
        
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)
        
        logger.info(f"Складови заявки експортирани в {file_path}")
        return file_path
    
    def export_vehicle_routes(self, solution: CVRPSolution) -> str:
        """Експортира маршрутите на превозните средства"""
        file_path = os.path.join(self.config.excel_output_dir, self.config.routes_excel_file)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        data = []
        for i, route in enumerate(solution.routes):
            vehicle_name = VEHICLE_SETTINGS.get(route.vehicle_type.value, {}).get('name', 'Неизвестен')
            for j, customer in enumerate(route.customers):
                data.append({
                    'Маршрут': i + 1,
                    'Превозно средство': vehicle_name,
                    'Ред в маршрута': j + 1,
                    'ID клиент': customer.id,
                    'Име клиент': customer.name,
                    'Обем (ст.)': customer.volume,
                    'GPS': customer.original_gps_data
                })
        
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)
        
        logger.info(f"Маршрути експортирани в {file_path}")
        return file_path


class OutputHandler:
    """Главен клас за обработка на изходни данни"""
    
    def __init__(self, config: Optional[OutputConfig] = None):
        self.config = config or get_config().output
        self.map_generator = InteractiveMapGenerator(self.config)
        self.excel_exporter = ExcelExporter(self.config)
    
    def generate_all_outputs(self, solution: CVRPSolution, 
                           warehouse_allocation: WarehouseAllocation,
                           depot_location: Tuple[float, float]) -> Dict[str, str]:
        """Генерира всички изходни файлове"""
        logger.info("Започвам генериране на изходни файлове")
        
        output_files = {}
        
        # Интерактивна карта (БЕЗ складови клиенти)
        if self.config.enable_interactive_map:
            route_map = self.map_generator.create_map(solution, warehouse_allocation, depot_location)
            map_file = self.map_generator.save_map(route_map)
            output_files['map'] = map_file
        
        # Excel файлове
        warehouse_file = self.excel_exporter.export_warehouse_orders(warehouse_allocation.warehouse_customers)
        if warehouse_file:
            output_files['warehouse_excel'] = warehouse_file
        
        routes_file = self.excel_exporter.export_vehicle_routes(solution)
        output_files['routes_excel'] = routes_file
        
        logger.info(f"Генерирани {len(output_files)} изходни файла")
        return output_files


# Удобна функция
def generate_outputs(solution: CVRPSolution, warehouse_allocation: WarehouseAllocation,
                   depot_location: Tuple[float, float]) -> Dict[str, str]:
    """Удобна функция за генериране на всички изходи"""
    handler = OutputHandler()
    return handler.generate_all_outputs(solution, warehouse_allocation, depot_location) 