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
        'color': 'red',
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
        
        # Проверяваме дали OSRM е достъпен
        try:
            import requests
            from config import get_config
            osrm_config = get_config().osrm
            test_url = f"{osrm_config.base_url.rstrip('/')}/route/v1/driving/23.3,42.7;23.3,42.7"
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                logger.info("✅ OSRM сървър е достъпен - ще използвам реални маршрути")
                self.use_osrm_routing = True
            else:
                logger.warning("⚠️ OSRM сървър не отговаря - ще използвам прави линии")
                self.use_osrm_routing = False
        except Exception as e:
            logger.warning(f"⚠️ Не мога да се свържа с OSRM сървъра: {e}")
            logger.warning("   Ще използвам прави линии за маршрутите")
            self.use_osrm_routing = False
    
    def create_map(self, solution: CVRPSolution, warehouse_allocation: WarehouseAllocation,
                  depot_location: Tuple[float, float]) -> folium.Map:
        """Създава интерактивна карта с маршрутите"""
        logger.info("Създавам интерактивна карта")
        
        # Показваме OSRM статуса
        if self.use_osrm_routing:
            logger.info("🛣️ Използвам OSRM Route API за реални маршрути")
        else:
            logger.warning("📐 Използвам прави линии (OSRM недостъпен)")
        
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
        """Получава реална геометрия на маршрута от OSRM Route API"""
        try:
            import requests
            from config import get_config
            
            # OSRM Route API заявка за пълна геометрия
            osrm_config = get_config().osrm
            base_url = osrm_config.base_url.rstrip('/')
            
            # Форматираме координатите за OSRM (lon,lat формат)
            start_lon, start_lat = start_coords[1], start_coords[0]
            end_lon, end_lat = end_coords[1], end_coords[0]
            
            route_url = f"{base_url}/route/v1/driving/{start_lon:.6f},{start_lat:.6f};{end_lon:.6f},{end_lat:.6f}?geometries=geojson&overview=full&steps=false"
            
            response = requests.get(route_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['code'] == 'Ok' and data['routes']:
                route = data['routes'][0]
                coordinates = route['geometry']['coordinates']
                
                # Конвертираме от [lon,lat] към [lat,lon] за Folium
                geometry = [(coord[1], coord[0]) for coord in coordinates]
                
                logger.debug(f"✅ OSRM геометрия получена: {len(geometry)} точки")
                return geometry
            else:
                logger.warning(f"OSRM Route API грешка: {data.get('message', 'Неизвестна грешка')}")
            return [start_coords, end_coords]
            
        except Exception as e:
            logger.warning(f"Грешка при OSRM Route API заявка: {e}")
            # Fallback към права линия
            return [start_coords, end_coords]
    
    def _get_full_route_geometry(self, waypoints: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Получава пълната геометрия за маршрут с множество точки от OSRM.
        Ако има твърде много точки, използваме fallback за по-бърза работа.
        """
        if len(waypoints) < 2:
            return waypoints

        # ОПТИМИЗАЦИЯ: Ако маршрутът има твърде много точки, не търсим пълна геометрия,
        # а чертаем сегменти, за да не претоварваме OSRM и да ускорим процеса.
        MAX_WAYPOINTS_FOR_FULL_GEOMETRY = 15
        if len(waypoints) > MAX_WAYPOINTS_FOR_FULL_GEOMETRY:
            logger.info(f"🌀 Маршрутът има {len(waypoints)} точки (> {MAX_WAYPOINTS_FOR_FULL_GEOMETRY}). "
                        f"Използвам опростена геометрия (сегменти) за по-бърза работа.")
            full_geometry = []
            for i in range(len(waypoints) - 1):
                # За всеки сегмент взимаме геометрията (или права линия при грешка)
                segment_geometry = self._get_osrm_route_geometry(waypoints[i], waypoints[i+1])
                if i > 0:
                    # Премахваме първата точка, за да няма дублиране
                    segment_geometry = segment_geometry[1:]
                full_geometry.extend(segment_geometry)
            return full_geometry

        try:
            import requests
            from config import get_config
            
            # OSRM Route API заявка за целия маршрут
            osrm_config = get_config().osrm
            base_url = osrm_config.base_url.rstrip('/')
            
            # Форматираме всички координати за OSRM (lon,lat формат)
            coords_str = ';'.join([f"{lon:.6f},{lat:.6f}" for lat, lon in waypoints])
            
            route_url = f"{base_url}/route/v1/driving/{coords_str}?geometries=geojson&overview=full&steps=false"
            
            response = requests.get(route_url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data['code'] == 'Ok' and data['routes']:
                route = data['routes'][0]
                coordinates = route['geometry']['coordinates']
                
                # Конвертираме от [lon,lat] към [lat,lon] за Folium
                geometry = [(coord[1], coord[0]) for coord in coordinates]
                
                logger.info(f"✅ OSRM маршрут геометрия получена: {len(geometry)} точки за {len(waypoints)} waypoints")
                return geometry
            else:
                logger.warning(f"OSRM Route API грешка за пълен маршрут: {data.get('message', 'Неизвестна грешка')}")
                return waypoints
                
        except Exception as e:
            logger.warning(f"Грешка при OSRM Route API заявка за пълен маршрут: {e}")
            # Fallback към последователност от прави линии
            full_geometry = []
            for i in range(len(waypoints) - 1):
                segment = self._get_osrm_route_geometry(waypoints[i], waypoints[i + 1])
                if i == 0:
                    full_geometry.extend(segment)
                else:
                    full_geometry.extend(segment[1:])  # Пропускаме дублираната точка
            
            return full_geometry if full_geometry else waypoints
    
    def _add_routes_to_map(self, route_map: folium.Map, routes: List[Route], depot_location: Tuple[float, float]):
        """Добавя маршрутите на картата с OSRM геометрия и филтър за бусовете"""
        # Създаваме FeatureGroup за всеки автобус
        bus_layers = {}
        
        for route_idx, route in enumerate(routes):
            vehicle_settings = VEHICLE_SETTINGS.get(route.vehicle_type.value, {
                'color': 'gray', 
                'icon': 'circle',
                'prefix': 'fa',
                'name': 'Неизвестен'
            })
            
            # Всеки автобус получава уникален цвят
            bus_color = BUS_COLORS[route_idx % len(BUS_COLORS)]
            bus_id = f"bus_{route_idx + 1}"
            
            # Създаваме FeatureGroup за този автобус
            bus_layer = folium.FeatureGroup(name=f"🚌 Автобус {route_idx + 1} ({len(route.customers)} клиента)")
            bus_layers[bus_id] = bus_layer
            
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
                    
                    # Добавяме номерирания маркер в слоя на автобуса
                    marker = folium.Marker(
                        customer.coordinates,
                        popup=folium.Popup(popup_text, max_width=300),
                        tooltip=f"#{client_number}: {customer.name}",
                        icon=folium.DivIcon(
                            html=icon_html,
                            icon_size=(30, 30),
                            icon_anchor=(15, 15),
                            popup_anchor=(0, -15)
                        )
                    )
                    marker.add_to(bus_layer)
            
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
                        # Създаваме popup с информация за маршрута
                        popup_text = f"""
                        <div style="font-family: Arial, sans-serif;">
                            <h4 style="margin: 0; color: {bus_color};">
                                🚌 Автобус {route_idx + 1} - {vehicle_settings['name']}
                            </h4>
                            <hr style="margin: 5px 0;">
                            <b>OSRM маршрут:</b> ✅<br>
                            <b>Клиенти:</b> {len(route.customers)}<br>
                            <b>Разстояние:</b> {route.total_distance_km:.1f} км<br>
                            <b>Време:</b> {route.total_time_minutes:.0f} мин<br>
                            <b>Обем:</b> {route.total_volume:.1f} ст.<br>
                            <b>Геометрия:</b> {len(route_geometry)} точки
                        </div>
                        """
                        
                        # Създаваме линията в слоя на автобуса
                        polyline = folium.PolyLine(
                            route_geometry,
                            color=bus_color,
                            weight=4,
                            opacity=0.8,
                            popup=folium.Popup(popup_text, max_width=300)
                        )
                        polyline.add_to(bus_layer)
                        logger.info(f"✅ OSRM маршрут добавен за Автобус {route_idx + 1}: {len(route_geometry)} точки")
                    else:
                        # Fallback към прави линии
                        popup_text = f"""
                        <div style="font-family: Arial, sans-serif;">
                            <h4 style="margin: 0; color: {bus_color};">
                                🚌 Автобус {route_idx + 1} - {vehicle_settings['name']}
                            </h4>
                            <hr style="margin: 5px 0;">
                            <b>OSRM маршрут:</b> ⚠️ (прави линии)<br>
                            <b>Клиенти:</b> {len(route.customers)}<br>
                            <b>Разстояние:</b> {route.total_distance_km:.1f} км<br>
                            <b>Време:</b> {route.total_time_minutes:.0f} мин<br>
                            <b>Обем:</b> {route.total_volume:.1f} ст.
                        </div>
                        """
                        
                        polyline = folium.PolyLine(
                            waypoints,
                            color=bus_color,
                            weight=3,
                            opacity=0.6,
                            popup=folium.Popup(popup_text, max_width=300),
                            dashArray='5, 5'  # Пунктирана линия за показване че не е OSRM
                        )
                        polyline.add_to(bus_layer)
                        logger.warning(f"⚠️ Използвам прави линии за Автобус {route_idx + 1}")
                        
                except Exception as e:
                    logger.error(f"❌ Грешка при OSRM маршрут за Автобус {route_idx + 1}: {e}")
                    # Fallback към прави линии
                    waypoints = [depot_location]
                    for customer in route.customers:
                        if customer.coordinates:
                            waypoints.append(customer.coordinates)
                    waypoints.append(depot_location)
                    
                    popup_text = f"""
                    <div style="font-family: Arial, sans-serif;">
                        <h4 style="margin: 0; color: {bus_color};">
                            🚌 Автобус {route_idx + 1} - {vehicle_settings['name']}
                        </h4>
                        <hr style="margin: 5px 0;">
                        <b>OSRM маршрут:</b> ❌ (fallback)<br>
                        <b>Клиенти:</b> {len(route.customers)}<br>
                        <b>Разстояние:</b> {route.total_distance_km:.1f} км<br>
                        <b>Време:</b> {route.total_time_minutes:.0f} мин<br>
                        <b>Обем:</b> {route.total_volume:.1f} ст.
                    </div>
                    """
                    
                    polyline = folium.PolyLine(
                        waypoints,
                        color=bus_color,
                        weight=3,
                        opacity=0.6,
                        popup=folium.Popup(popup_text, max_width=300),
                        dashArray='5, 5'
                    )
                    polyline.add_to(bus_layer)
            
            elif route.customers:
                # Fallback към прави линии ако OSRM е изключен
                waypoints = [depot_location]
                for customer in route.customers:
                    if customer.coordinates:
                        waypoints.append(customer.coordinates)
                waypoints.append(depot_location)
                
                polyline = folium.PolyLine(
                    waypoints,
                    color=bus_color,
                    weight=3,
                    opacity=0.8,
                    popup=f"🚌 Автобус {route_idx + 1} - {vehicle_settings['name']}"
                )
                polyline.add_to(bus_layer)
        
        # Добавяме всички слоеве на автобусите към картата
        for bus_layer in bus_layers.values():
            bus_layer.add_to(route_map)
        
        # Добавяме LayerControl за филтър
        folium.LayerControl(
            position='topright',
            collapsed=False,
            overlay=True,
            control=True
                ).add_to(route_map)
    
    def _add_legend(self, route_map: folium.Map, routes: List[Route]):
        """Добавя легенда на картата с информация за маршрутите"""
        # Изчисляваме статистики
        total_distance = sum(route.total_distance_km for route in routes)
        total_time = sum(route.total_time_minutes for route in routes)
        total_volume = sum(route.total_volume for route in routes)
        osrm_routes = sum(1 for route in routes if self.use_osrm_routing)
        
        legend_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 10px; width: 280px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px; border-radius: 5px;
                    box-shadow: 0 0 15px rgba(0,0,0,0.2);">
        <h4 style="margin-top:0; margin-bottom:10px; text-align: center;">🗺️ Информация</h4>
        '''
        
        # Добавяме депо
        legend_html += '''
        <p style="margin: 5px 0;">
            <i class="fa fa-home" style="color: black; margin-right: 8px;"></i>
            Депо
        </p>
        '''
        
        # Добавяме информация за филтъра
        legend_html += '''
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0; font-weight: bold;">🚌 Филтър на автобуси:</p>
        <p style="margin: 5px 0; font-size: 12px; color: #666;">
            Използвай контрола в горния десен ъгъл за показване/скриване на отделни автобуси
            </p>
            '''
        
        # Добавяме информация за OSRM маршрутите
        osrm_status = "🛣️ OSRM маршрути" if self.use_osrm_routing else "📐 Прави линии"
        
        legend_html += f'''
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0; font-size: 12px; color: #666;">
            Числата показват реда на посещение<br>
            {osrm_status}
        </p>
        '''
        
        # Добавяме статистики
        legend_html += f'''
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0; font-size: 12px; font-weight: bold;">
            📊 Статистики:
        </p>
        <p style="margin: 3px 0; font-size: 11px; color: #555;">
            • Общо разстояние: {total_distance:.1f} км<br>
            • Общо време: {total_time:.0f} мин<br>
            • Общ обем: {total_volume:.1f} ст.<br>
            • OSRM маршрути: {osrm_routes}/{len(routes)}
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
        df.to_excel(file_path, index=False, engine='openpyxl')
        
        logger.info(f"Маршрути експортирани в {file_path}")
        return file_path


class OutputHandler:
    """Главен клас за управление на изходните данни"""
    
    def __init__(self, config: Optional[OutputConfig] = None):
        self.config = config or get_config().output
        self.excel_exporter = ExcelExporter(self.config)
    
    def generate_all_outputs(self, solution: CVRPSolution, 
                           warehouse_allocation: WarehouseAllocation,
                           depot_location: Tuple[float, float]) -> Dict[str, str]:
        """Генерира всички изходни файлове и връща речник с пътищата до тях"""
        logger.info("Започвам генериране на изходни файлове")
        output_files = {}

        # 1. Интерактивна карта
        if self.config.enable_interactive_map:
            map_gen = InteractiveMapGenerator(self.config)
            route_map = map_gen.create_map(solution, warehouse_allocation, depot_location)
            map_file = map_gen.save_map(route_map)
            output_files['map'] = map_file
        
        # 2. Обединяване на всички необслужени клиенти и експорт
        all_unserviced_customers = warehouse_allocation.warehouse_customers + solution.dropped_customers
        if all_unserviced_customers:
            logger.info(f"Общо необслужени клиенти (склад + пропуснати): {len(all_unserviced_customers)}")
            warehouse_file = self.excel_exporter.export_warehouse_orders(all_unserviced_customers)
            if warehouse_file:
                output_files['warehouse_excel'] = warehouse_file
        
        # 3. Експорт на маршрутите
        if solution.routes:
            routes_file = self.excel_exporter.export_vehicle_routes(solution)
            if routes_file:
                output_files['routes_excel'] = routes_file
        
        logger.info(f"Генерирани {len(output_files)} изходни файла")
        return output_files


# Удобна функция
def generate_outputs(solution: CVRPSolution, warehouse_allocation: WarehouseAllocation,
                   depot_location: Tuple[float, float]) -> Dict[str, str]:
    """Удобна функция за генериране на всички изходи"""
    handler = OutputHandler()
    return handler.generate_all_outputs(solution, warehouse_allocation, depot_location) 