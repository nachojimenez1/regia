"""Clima actual de Monterrey. Responsable: persona 3."""
import json
import urllib.error
import urllib.request
from django.core.cache import cache
from core.contracts import Weather

CACHE_KEY = "conditions:monterrey_weather"
CACHE_TTL_SECONDS = 600  # 600'' = 10'
MONTERREY_WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=25.6866&longitude=-100.3161"
    "&current=temperature_2m,precipitation,rain"
)

def fetch_weather() -> Weather | None:
    """Consulta el clima actual en una API externa y lo devuelve como Weather.

    Requisitos:

    - Si la API falla o tarda demasiado, devuelve None. Nunca lanza una
      excepción: la aplicación tiene que seguir calculando rutas sin clima.
    - Poned un tiempo máximo corto a la petición (unos pocos segundos).
    - Guardad el resultado unos minutos para no llamar a la API en cada
      consulta de ruta (django.core.cache sirve para esto).

    Propuesta: Open-Meteo. Comprobad en su documentación las condiciones de
    uso y si pide clave antes de integrarla, y citadla en la memoria.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
      return cached
    
    try: 
      req = urllib.request.Request(MONTERREY_WEATHER_URL, 
            headers={"User-Agent": "RegiaMetrorreyCopilot/1.0"},)

      with urllib.request.urlopen(req, timeout=3.0) as response:
        if response.status != 200:
                return None
        payload = json.loads(response.read().decode("utf-8"))

      current = payload["current"]
      temp_c = float(current["temperature_2m"])
      precip_mm = float(current.get("precipitation", 0.0))
      rein_mm = float(current.get("rain", 0.0))

      weather = Weather(temperature_c=temp_c, precipitation_mm=precip_mm, is_raining=(precip_mm > 0.0 or rain_mm > 0.0),)
      cache.set(CACHE_KEY, weather, timeout=CACHE_TTL_SECONDS)
      return weather

    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, TypeError, json.JSONDecodeError):
      return None
