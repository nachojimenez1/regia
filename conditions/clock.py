"""Hora de Monterrey, horario de servicio y frecuencias. Responsable: persona 3."""
from datetime import datetime, time
from django.utils import timezone


def now_monterrey() -> datetime:
    """Devuelve la hora actual de Monterrey, con zona horaria.

    settings.TIME_ZONE ya es "America/Monterrey", así que
    django.utils.timezone.localtime() da esta hora directamente.
    """
    return timezone.localtime()


def is_service_open(when: datetime) -> bool:
    """Indica si el metro da servicio en ese instante.

    Horario habitual de Metrorrey: de 04:45 a 24:00 (00:00).
    """
    if timezone.is_naive(when):
        when = timezone.make_aware(when)
    else:
        when = timezone.localtime(when)

    hora = when.time()
    # El metro abre a las 4:45 de la mañana y cierra a medianoche (00:00)
    return hora >= time(4, 45)


def headways(when: datetime) -> dict[str, float]:
    """Minutos entre trenes en cada línea a esa hora: {"L1": ..., "L2": ..., "L3": ...}.

    Distingue entre días laborables y fines de semana, y entre hora punta y hora valle.
    """
    if timezone.is_naive(when):
        when = timezone.make_aware(when)
    else:
        when = timezone.localtime(when)

    hora = when.time()
    dia_semana = when.weekday()  # 0 = lunes, ..., 4 = viernes, 5 = sábado, 6 = domingo

    # Fin de semana (sábado o domingo)
    if dia_semana >= 5:
        if time(12, 0) <= hora <= time(19, 0):
            return {"L1": 6.0, "L2": 6.5, "L3": 7.0}
        return {"L1": 8.0, "L2": 8.5, "L3": 9.0}

    # Días laborables (lunes a viernes): hora punta por la mañana o por la tarde
    es_punta_manana = time(6, 30) <= hora <= time(9, 30)
    es_punta_tarde = time(17, 0) <= hora <= time(20, 30)

    if es_punta_manana or es_punta_tarde:
        return {"L1": 3.5, "L2": 4.0, "L3": 4.5}

    # Resto del día laborable (hora valle)
    return {"L1": 5.5, "L2": 6.0, "L3": 6.5}