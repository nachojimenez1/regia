from core.contracts import NodeId, Graph
import math

RADIO_TIERRA_METROS = 6371000.0
VELOCIDAD_MAXIMA_MONTERREY_KPH = 80

def haversine_meters(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi/2) ** 2) + math.cos(phi1)*math.cos(phi2)*(math.sin(delta_lambda/2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return RADIO_TIERRA_METROS * c

def meters_to_minutes(meters):
    speed_in_meterspermin = (VELOCIDAD_MAXIMA_MONTERREY_KPH*1000) / 60
    return meters/speed_in_meterspermin




def estimate(graph: Graph, node: NodeId, destination: str) -> float:
    current_station_id = node[0]
    if current_station_id == destination:
        return 0.0
    curr_info = graph.stations[current_station_id]
    dest_info = graph.stations[destination]
    distance_meters = haversine_meters(curr_info.lat, curr_info.lon, dest_info.lat, dest_info.lon)
    return meters_to_minutes(distance_meters)