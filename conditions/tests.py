"""Tests de condiciones. Responsable: persona 3.

PENDIENTE. Comprobaciones útiles:

- headways() da frecuencias distintas en hora punta y en hora valle.
- is_service_open() es False de madrugada y True a mediodía.
- fetch_weather() devuelve None si la API falla (simulad el fallo con
  unittest.mock; los tests no deben depender de internet).
- get_context() solo incluye las incidencias activas.

Se ejecutan con: python manage.py test conditions
"""
from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo
from django.core.cache import cache
from django.test import TestCase
from core.contracts import IncidentKind, Weather
from .clock import headways, is_service_open
from .context import get_context
from .models import NetworkIncident
from .weather import CACHE_KEY, fetch_weather

MTY_TZ = ZoneInfo("America/Monterrey")

class ClockTest(TestCase):
    def test_service_open_and_closed_hours(self):
        madrugada = datetime(2026, 11, 24, 3, 15, tzinfo=MTY_TZ)
        mediodia = datetime(2026, 11, 24, 12, 30, tzinfo=MTY_TZ)
        medianoche = datetime(2026, 11, 24, 0, 10, tzinfo=MTY_TZ)

        self.assertFalse(is_service_open(madrugada))
        self.assertTrue(is_service_open(mediodia))
        self.assertFalse(is_service_open(medianoche))

    def test_headways_peak_vs_offpeak_and_weekend(self):
        punta_laborable = datetime(2026, 11, 24, 8, 0, tzinfo=MTY_TZ)
        valle_laborable = datetime(2026, 11, 24, 14, 0, tzinfo=MTY_TZ)
        domingo = datetime(2026, 11, 29, 9, 0, tzinfo=MTY_TZ)

        hw_punta = headways(punta_laborable)
        hw_valle = headways(valle_laborable)
        hw_finde = headways(domingo)

        self.assertLess(hw_punta["L1"], hw_valle["L1"])
        self.assertLess(hw_valle["L1"], hw_finde["L1"])

class WeatherTest(TestCase):
  def setUp(self):
    cache.delete(CACHE_KEY)
  
  @patch("conditions.weather.urllib.request.urlopen")
  def test_fetch_weather_success_and_cache(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = (
            b'{"current": {"temperature_2m": 28.5, "precipitation": 1.2, "rain": 1.2}}'
        )
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        weather = fetch_weather()
        self.assertEqual(weather, Weather(temperature_c=28.5, precipitation_mm=1.2, is_raining=True))
        self.assertEqual(mock_urlopen.call_count, 1)

        weather_cached = fetch_weather()
        self.assertEqual(weather_cached, weather)
        self.assertEqual(mock_urlopen.call_count, 1)
  
  @patch("conditions.weather.urllib.request.urlopen", side_effect=TimeoutError("Timeout"))
  def test_fetch_weather_returns_none_on_error(self, _mock_urlopen):
        self.assertIsNone(fetch_weather())


class ContextTests(TestCase):
    def setUp(self):
        cache.delete(CACHE_KEY)
        NetworkIncident.objects.create(kind=IncidentKind.STATION_CLOSED.value, station_id="cuauhtemoc",
            extra_minutes=0.0, description="Cierre por mantenimiento", is_active=True,)
        NetworkIncident.objects.create(kind=IncidentKind.LINE_DELAY.value, line_id="L2", extra_minutes=6.0,
            description="Retraso simulado inactivo", is_active=False,)

    @patch("conditions.context.fetch_weather")
    def test_get_context_filters_only_active_incidents(self, mock_weather):
        mock_weather.return_value = Weather(temperature_c=24.0, precipitation_mm=0.0, is_raining=False)

        ctx = get_context()
        self.assertEqual(len(ctx.incidents), 1)
        self.assertEqual(ctx.incidents[0].station_id, "cuauhtemoc")
        self.assertIsNotNone(ctx.weather)

    def test_get_context_future_time_sets_weather_none(self):
        future_dt = datetime(2026, 11, 25, 10, 0, tzinfo=MTY_TZ)
        ctx = get_context(when=future_dt)
        self.assertIsNone(ctx.weather)
        self.assertEqual(ctx.when, future_dt)