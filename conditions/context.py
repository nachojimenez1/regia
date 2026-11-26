"""Construcción del Context. Responsable: persona 3.

Este archivo es la única puerta de entrada al módulo: el resto del proyecto
solo llama a get_context().
"""
from datetime import datetime
from django.utils import timezone
from core.contracts import Context, Incident, IncidentKind
from .clock import headways, is_service_open, now_monterrey
from .models import NetworkIncident
from .weather import fetch_weather

def get_context(when: datetime | None = None) -> Context:
    """Reúne hora, frecuencias, clima e incidencias activas en un Context.

    - when=None significa "ahora" (conditions.clock.now_monterrey()).
    - Si when es otra hora (el usuario planifica un viaje futuro), el clima
      actual no aplica: decidid si se deja en None o se usa una previsión.
    - Las incidencias salen de la base de datos (solo las activas),
      convertidas a core.contracts.Incident.
    """
    if when is None:
        target_when = now_monterrey()
        current_weather = fetch_weather()
    else:
        target_when = timezone.make_aware(when) if timezone.is_naive(when) else timezone.localtime(when)
        current_weather = None
    
    active_records = NetworkIncident.objects.filter(is_active=True)
    incidents = tuple(
        Incident(kind=IncidentKind(rec.kind), station_id=rec.station_id or None, line_id=rec.line_id or None,
            extra_minutes=float(rec.extra_minutes), description=rec.description,)
        for rec in active_records
    )

    return Context(when=target_when, service_open=is_service_open(target_when), headways=headways(target_when),
        weather=current_weather, incidents=incidents,)

    