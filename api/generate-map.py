from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import folium
import requests
import json
from typing import List, Tuple
import time

app = Flask(__name__)
CORS(app)  # Permite requisições do frontend

class RouteVisualizer:
    def __init__(self):
        # Coordenadas do Biopark Educação - Toledo, PR
        self.destination = {
            'name': 'Biopark Educação - Toledo, PR',
            'lat': -24.7136,
            'lon': -53.7405,
            'address': 'R. da Faculdade, 645 - Jardim La Salle, Toledo - PR, 85902-532'
        }
    
    def geocode_address(self, address: str) -> Tuple[float, float]:
        """Converte endereço em coordenadas usando Nominatim (OpenStreetMap)"""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'br'  # Limita busca ao Brasil
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
            else:
                raise Exception(f"Endereço não encontrado: {address}")
                
        except Exception as e:
            raise Exception(f"Erro na geocodificação: {str(e)}")
    
    def get_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> dict:
        """Obtém rota usando OSRM (Open Source Routing Machine)"""
        try:
            url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
            params = {
                'overview': 'full',
                'geometries': 'geojson'
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data['code'] == 'Ok' and data['routes']:
                route = data['routes'][0]
                return {
                    'geometry': route['geometry']['coordinates'],
                    'distance': route['distance'] / 1000,  # Converte para km
                    'duration': route['duration'] / 60     # Converte para minutos
                }
            else:
                raise Exception("Rota não encontrada")
                
        except Exception as e:
            raise Exception(f"Erro ao calcular rota: {str(e)}")
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distância em linha reta entre dois pontos (Haversine)"""
        import math
        
        R = 6371  # Raio da Terra em km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def create_map_html(self, origins: List[dict]) -> str:
        """Cria mapa HTML com as rotas"""
        try:
            # Calcula centro do mapa baseado nas coordenadas
            all_lats = [origin['lat'] for origin in origins] + [self.destination['lat']]
            all_lons = [origin['lon'] for origin in origins] + [self.destination['lon']]
            
            center_lat = sum(all_lats) / len(all_lats)
            center_lon = sum(all_lons) / len(all_lons)
            
            # Cria mapa
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles='OpenStreetMap'
            )
            
            # Adiciona marcador do destino (Biopark)
            folium.Marker(
                [self.destination['lat'], self.destination['lon']],
                popup=folium.Popup(f"<b>{self.destination['name']}</b><br>{self.destination['address']}", max_width=300),
                tooltip=self.destination['name'],
                icon=folium.Icon(color='red', icon='graduation-cap', prefix='fa')
            ).add_to(m)
            
            # Cores para as rotas
            colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 
                     'beige', 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple', 'white', 
                     'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
            
            # Adiciona cada origem e sua rota
            for i, origin in enumerate(origins):
                color = colors[i % len(colors)]
                
                # Marcador da origem
                folium.Marker(
                    [origin['lat'], origin['lon']],
                    popup=folium.Popup(
                        f"<b>Origem {i+1}</b><br>"
                        f"<b>Endereço:</b> {origin['address']}<br>"
                        f"<b>Distância:</b> {origin.get('distance', 'N/A'):.1f} km<br>"
                        f"<b>Tempo:</b> {origin.get('duration', 'N/A'):.0f} min",
                        max_width=300
                    ),
                    tooltip=f"Origem {i+1}",
                    icon=folium.Icon(color=color, icon='home', prefix='fa')
                ).add_to(m)
                
                # Adiciona rota se disponível
                if 'route_geometry' in origin and origin['route_geometry']:
                    # Converte coordenadas [lon, lat] para [lat, lon] para o Folium
                    route_coords = [[coord[1], coord[0]] for coord in origin['route_geometry']]
                    
                    folium.PolyLine(
                        route_coords,
                        color=color,
                        weight=4,
                        opacity=0.8,
                        popup=f"Rota {i+1}: {origin.get('distance', 'N/A'):.1f} km, {origin.get('duration', 'N/A'):.0f} min"
                    ).add_to(m)
            
            # Ajusta zoom para mostrar todos os pontos
            if len(origins) > 0:
                m.fit_bounds([[min(all_lats), min(all_lons)], [max(all_lats), max(all_lons)]])
            
            return m._repr_html_()
            
        except Exception as e:
            raise Exception(f"Erro ao criar mapa: {str(e)}")

# Instancia o visualizador
visualizer = RouteVisualizer()

@app.route('/generate-map', methods=['POST'])
def generate_map():
    """Endpoint para gerar mapa com rotas"""
    try:
        data = request.get_json()
        
        if not data or 'origins' not in data:
            return jsonify({
                'success': False,
                'error': 'Lista de origens é obrigatória'
            }), 400
        
        origins_data = data['origins']
        addresses = [origin['address'] for origin in origins_data]
        
        if not addresses or len(addresses) == 0:
            return jsonify({
                'success': False,
                'error': 'Pelo menos um endereço deve ser fornecido'
            }), 400
        
        origins = []
        
        for i, address in enumerate(addresses):
            if not address.strip():
                continue
                
            try:
                # Geocodifica endereço
                lat, lon = visualizer.geocode_address(address)
                
                # Calcula rota
                route_info = visualizer.get_route(
                    lat, lon,
                    visualizer.destination['lat'], 
                    visualizer.destination['lon']
                )
                
                origin_data = {
                    'address': address,
                    'lat': lat,
                    'lon': lon,
                    'distance': route_info['distance'],
                    'duration': route_info['duration'],
                    'route_geometry': route_info['geometry']
                }
                
                origins.append(origin_data)
                
            except Exception as e:
                # Se falhar, adiciona sem rota
                try:
                    lat, lon = visualizer.geocode_address(address)
                    distance = visualizer.calculate_distance(
                        lat, lon,
                        visualizer.destination['lat'], 
                        visualizer.destination['lon']
                    )
                    
                    origin_data = {
                        'address': address,
                        'lat': lat,
                        'lon': lon,
                        'distance': distance,
                        'duration': distance * 1.5,  # Estimativa: 1.5 min por km
                        'route_geometry': None,
                        'error': f"Rota não disponível: {str(e)}"
                    }
                    
                    origins.append(origin_data)
                    
                except Exception as geo_error:
                    return jsonify({
                        'success': False,
                        'error': f"Erro no endereço '{address}': {str(geo_error)}"
                    }), 400
        
        if not origins:
            return jsonify({
                'success': False,
                'error': 'Nenhum endereço válido foi processado'
            }), 400
        
        # Gera mapa HTML
        map_html = visualizer.create_map_html(origins)
        
        return jsonify({
            'success': True,
            'mapHtml': map_html,
            'origins': origins,
            'destination': visualizer.destination
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f"Erro interno: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'OK',
        'service': 'Route Visualizer API',
        'destination': visualizer.destination
    })