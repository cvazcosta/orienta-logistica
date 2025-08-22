from http.server import BaseHTTPRequestHandler
import os
import folium
import requests
import json
from typing import List, Tuple
import time
import urllib.parse
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

class RouteVisualizer:
    def __init__(self):
        # Coordenadas do Biopark Educação - Toledo, PR
        self.destination = {
            'name': 'Biopark Educação - Toledo, PR',
            'lat': -24.617465183385058,
            'lon': -53.70939297263396,
            'address': 'Biopark, Edifício Charles Darwin - Avenida Max Planck, 3797 - Toledo, PR, 85920-025'
        }
        # Cache para coordenadas geocodificadas
        self.geocode_cache = {}
        # Cache para rotas calculadas
        self.route_cache = {}
    
    def geocode_address(self, address: str) -> Tuple[float, float]:
        """Geocodifica um endereço usando a API do Nominatim com cache"""
        # Verifica se o endereço já está no cache
        if address in self.geocode_cache:
            print(f"DEBUG: Usando coordenadas do cache para: {address}")
            return self.geocode_cache[address]
            
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'br'  # Limita busca ao Brasil
            }
            
            # Headers para identificar a aplicação
            headers = {
                'User-Agent': 'RouteVisualizer/1.0 (contact@example.com)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            data = response.json()
            
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                
                # Armazena no cache
                self.geocode_cache[address] = (lat, lon)
                print(f"DEBUG: Coordenadas geocodificadas e armazenadas no cache: {address} -> {lat}, {lon}")
                
                return lat, lon
            else:
                raise Exception(f"Endereço não encontrado: {address}")
                
        except Exception as e:
            raise Exception(f"Erro na geocodificação: {str(e)}")
    
    def get_route(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> dict:
        """Obtém rota entre dois pontos usando OSRM com cache"""
        # Cria chave única para o cache baseada nas coordenadas
        cache_key = f"{start_lat:.6f},{start_lon:.6f}-{end_lat:.6f},{end_lon:.6f}"
        
        # Verifica se a rota já está no cache
        if cache_key in self.route_cache:
            print(f"DEBUG: Usando rota do cache para: {cache_key}")
            return self.route_cache[cache_key]
            
        try:
            url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
            params = {
                'overview': 'full',
                'geometries': 'geojson'
            }
            
            response = requests.get(url, params=params, timeout=8)
            data = response.json()
            
            if data['code'] == 'Ok' and data['routes']:
                route = data['routes'][0]
                route_info = {
                    'geometry': route['geometry']['coordinates'],
                    'distance': route['distance'] / 1000,  # Converte para km
                    'duration': route['duration'] / 60     # Converte para minutos
                }
                
                # Armazena no cache
                self.route_cache[cache_key] = route_info
                print(f"DEBUG: Rota calculada e armazenada no cache: {cache_key}")
                
                return route_info
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

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Verificar se é a rota correta
            if self.path != '/api/generate-map':
                self.send_error(404, 'Not Found')
                return
            
            # Ler o corpo da requisição
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Parse do JSON
            try:
                data = json.loads(post_data.decode('utf-8'))
                print(f"DEBUG: Dados recebidos: {data}")
            except json.JSONDecodeError as e:
                print(f"DEBUG: Erro de JSON: {str(e)}")
                print(f"DEBUG: Dados brutos: {post_data.decode('utf-8')}")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'JSON inválido'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            # Validar dados - aceita tanto 'origins' quanto 'selectedOrigins'
            origins_key = 'selectedOrigins' if 'selectedOrigins' in data else 'origins'
            print(f"DEBUG: Chave encontrada: {origins_key}")
            print(f"DEBUG: Chaves disponíveis: {list(data.keys()) if data else 'None'}")
            
            if not data or origins_key not in data:
                print(f"DEBUG: Falha na validação - data: {bool(data)}, origins_key in data: {origins_key in data if data else False}")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Lista de origens é obrigatória'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            origins_data = data[origins_key]
            print(f"DEBUG: origins_data: {origins_data}")
            
            # Se for selectedOrigins, é uma lista de strings; se for origins, é uma lista de objetos
            if origins_key == 'selectedOrigins':
                addresses = origins_data  # Lista direta de endereços
            else:
                # Para origins, verificar se tem address ou usar coordenadas
                addresses = []
                for origin in origins_data:
                    if origin.get('address'):
                        addresses.append(origin['address'])
                    elif origin.get('lat') and origin.get('lon'):
                        # Usar coordenadas como fallback
                        addresses.append(f"{origin['lat']},{origin['lon']}")
                    elif origin.get('name'):
                        # Usar nome como fallback
                        addresses.append(origin['name'])
            
            print(f"DEBUG: addresses processados: {addresses}")
            
            # Filtrar endereços None ou vazios
            addresses = [addr for addr in addresses if addr and str(addr).strip()]
            
            if not addresses or len(addresses) == 0:
                print(f"DEBUG: Falha na validação de endereços - addresses: {addresses}")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Pelo menos um endereço válido deve ser fornecido'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            # Função para processar cada endereço individualmente
            def process_address(address):
                if not address or not address.strip():
                    return None
                    
                try:
                    print(f"DEBUG: Tentando geocodificar: {address}")
                    
                    # Se o endereço já são coordenadas, usar diretamente
                    if ',' in address and len(address.split(',')) == 2:
                        try:
                            lat, lon = map(float, address.split(','))
                            print(f"DEBUG: Coordenadas extraídas: lat={lat}, lon={lon}")
                        except ValueError:
                            # Se não conseguir converter, geocodificar normalmente
                            lat, lon = visualizer.geocode_address(address)
                    else:
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
                    
                    print(f"DEBUG: Origin processado com sucesso: {origin_data['address']}")
                    return origin_data
                    
                except Exception as e:
                    print(f"DEBUG: Erro na rota para {address}: {str(e)}")
                    # Se falhar, adiciona sem rota
                    try:
                        # Se o endereço já são coordenadas, usar diretamente
                        if ',' in address and len(address.split(',')) == 2:
                            try:
                                lat, lon = map(float, address.split(','))
                                print(f"DEBUG: Coordenadas extraídas (fallback): lat={lat}, lon={lon}")
                            except ValueError:
                                lat, lon = visualizer.geocode_address(address)
                        else:
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
                        
                        print(f"DEBUG: Origin processado sem rota: {origin_data['address']}")
                        return origin_data
                        
                    except Exception as geo_error:
                        print(f"DEBUG: Erro crítico na geocodificação de {address}: {str(geo_error)}")
                        return {'error': f"Erro no endereço '{address}': {str(geo_error)}", 'address': address}
            
            # Processamento paralelo dos endereços
            origins = []
            errors = []
            
            print(f"DEBUG: Iniciando processamento paralelo de {len(addresses)} endereços")
            start_time = time.time()
            
            # Otimização: processar em lotes para evitar sobrecarga de API
            batch_size = 5  # Processar 5 endereços por vez
            max_workers = min(3, len(addresses))  # Reduzir threads para evitar rate limiting
            
            # Processar endereços em lotes
            for i in range(0, len(addresses), batch_size):
                batch = addresses[i:i + batch_size]
                print(f"DEBUG: Processando lote {i//batch_size + 1} com {len(batch)} endereços")
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submeter tarefas do lote atual
                    future_to_address = {executor.submit(process_address, addr): addr for addr in batch}
                    
                    # Coletar resultados do lote
                    for future in as_completed(future_to_address):
                        result = future.result()
                        if result:
                            if 'error' in result and 'address' in result:
                                errors.append(result)
                            else:
                                origins.append(result)
                
                # Pequena pausa entre lotes para evitar rate limiting
                if i + batch_size < len(addresses):
                    time.sleep(0.5)  # 500ms de pausa entre lotes
            
            processing_time = time.time() - start_time
            print(f"DEBUG: Processamento paralelo concluído em {processing_time:.2f}s")
            
            # Se houver erros críticos, retornar erro
            if errors and not origins:
                error_msg = "; ".join([err['error'] for err in errors[:3]])  # Mostrar apenas os 3 primeiros erros
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': f'Erros de geocodificação: {error_msg}'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            if not origins:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Nenhum endereço válido foi processado'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            # Gera mapa HTML
            map_html = visualizer.create_map_html(origins)
            
            # Resposta de sucesso
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'success': True,
                'mapHtml': map_html,
                'origins': origins,
                'destination': visualizer.destination
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            print(f"Erro ao gerar mapa: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': f'Erro interno: {str(e)}'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_GET(self):
        # Health check
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                'status': 'OK',
                'service': 'Route Visualizer API',
                'destination': visualizer.destination
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, 'Not Found')
    
    def do_OPTIONS(self):
        # Suporte para CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()