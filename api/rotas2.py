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
        # Destino fixo: Biopark Educação, Toledo-PR
        self.destination = {
            'name': 'Biopark Educação',
            'lat': -24.61753714858977,
            'lon': -53.70958360848524,
            'address': 'Toledo-PR, CEP 85920-025'
        }
        
        # Cores para diferentes rotas
        self.colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 
                      'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 
                      'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 
                      'gray', 'black', 'lightgray']
    
    def geocode_address(self, address: str) -> Tuple[float, float]:
        """
        Converte endereço em coordenadas usando Nominatim (OpenStreetMap)
        """
        url = f"https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'br'  # Limita busca ao Brasil
        }
        
        headers = {'User-Agent': 'RouteVisualizer/1.0'}
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return lat, lon
        
        return None, None
    
    def get_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> dict:
        """
        Obtém rota usando OSRM (gratuito)
        """
        url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
        params = {
            'overview': 'full',
            'geometries': 'geojson'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data['routes']:
                route = data['routes'][0]
                return {
                    'coordinates': route['geometry']['coordinates'],
                    'distance': route['distance'] / 1000,  # Converter para km
                    'duration': route['duration'] / 60     # Converter para minutos
                }
        
        # Se não conseguir rota, retorna linha reta
        return {
            'coordinates': [[start_lon, start_lat], [end_lon, end_lat]],
            'distance': self.calculate_distance(start_lat, start_lon, end_lat, end_lon),
            'duration': 0
        }
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcula distância aproximada em km usando fórmula haversine
        """
        from math import radians, cos, sin, asin, sqrt
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        return 2 * asin(sqrt(a)) * 6371  # Raio da Terra em km
    
    def create_map_html(self, origins: List[dict]) -> str:
        """
        Cria mapa e retorna o HTML como string
        """
        # Calcula centro do mapa baseado em todos os pontos
        all_lats = [self.destination['lat']] + [origin['lat'] for origin in origins if origin['lat']]
        all_lons = [self.destination['lon']] + [origin['lon'] for origin in origins if origin['lon']]
        
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)
        
        # Cria o mapa
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            tiles='OpenStreetMap'
        )
        
        # Adiciona marcador do destino (Biopark)
        folium.Marker(
            [self.destination['lat'], self.destination['lon']],
            popup=f"<b>{self.destination['name']}</b><br>{self.destination['address']}",
            tooltip="Destino: Biopark Educação",
            icon=folium.Icon(color='red', icon='star')
        ).add_to(m)
        
        # Adiciona rotas e marcadores para cada origem
        for i, origin in enumerate(origins):
            if origin['lat'] is None or origin['lon'] is None:
                continue
                
            color = self.colors[i % len(self.colors)]
            
            # Adiciona marcador da origem com informações extras
            popup_content = f"<b>Origem {i+1}: {origin['name']}</b>"
            
            # Adiciona informações extras se disponíveis
            if 'info' in origin and origin['info']:
                info = origin['info']
                popup_content += f"<br><b>Data:</b> {info.get('data', 'N/A')}"
                popup_content += f"<br><b>Horário:</b> {info.get('horarioSaida', 'N/A')} - {info.get('horarioRetorno', 'N/A')}"
                popup_content += f"<br><b>Passageiros:</b> {info.get('passageiros', 'N/A')}"
                popup_content += f"<br><b>Turno:</b> {info.get('turno', 'N/A')}"
            
            folium.Marker(
                [origin['lat'], origin['lon']],
                popup=popup_content,
                tooltip=f"Origem: {origin['name']}",
                icon=folium.Icon(color=color, icon='play')
            ).add_to(m)
            
            # Obtém e adiciona rota
            route_data = self.get_route(
                origin['lat'], origin['lon'],
                self.destination['lat'], self.destination['lon']
            )
            
            # Converte coordenadas para formato do Folium (lat, lon)
            route_coords = [[coord[1], coord[0]] for coord in route_data['coordinates']]
            
            # Adiciona linha da rota
            folium.PolyLine(
                route_coords,
                color=color,
                weight=4,
                opacity=0.8,
                popup=f"Rota {i+1}: {route_data['distance']:.1f} km"
            ).add_to(m)
        
        # Retorna o HTML do mapa
        return m._repr_html_()

# Instância global do visualizador
visualizer = RouteVisualizer()

@app.route('/generate-map', methods=['POST'])
def generate_map():
    data = request.get_json()
    origins_data = data['origins']
    
    # Processa cada origem
    origins = []
    for origin_data in origins_data:
        if origin_data['type'] == 'address':
            # Geocodifica endereço
            lat, lon = visualizer.geocode_address(origin_data['address'])
            origins.append({
                'name': origin_data['name'],
                'lat': lat,
                'lon': lon,
                'info': origin_data.get('info', {})  # Adiciona informações extras
            })
        else:
            # Usa coordenadas diretamente
            origins.append({
                'name': origin_data['name'],
                'lat': origin_data['lat'],
                'lon': origin_data['lon'],
                'info': origin_data.get('info', {})  # Adiciona informações extras
            })
    
    # Gera o HTML do mapa
    map_html = visualizer.create_map_html(origins)
    
    return jsonify({
        'mapHtml': map_html,
        'message': 'Mapa gerado com sucesso'
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'API funcionando!'})

# Para Vercel, não precisamos das rotas de arquivos estáticos
# O Vercel gerencia isso automaticamente

# Para o Vercel, a aplicação Flask deve estar disponível no nível do módulo
# A variável 'app' é automaticamente detectada pelo Vercel

if __name__ == "__main__":
    # Instalar dependências necessárias:
    # pip install flask flask-cors folium requests
    
    print("🚀 Iniciando API do Visualizador de Rotas...")
    print("📍 Destino: Biopark Educação - Toledo, PR")
    print("🌐 API rodando em: http://localhost:5000")
    print("✅ Para testar: http://localhost:5000/health")
    
    app.run(debug=True, host='0.0.0.0', port=5000)