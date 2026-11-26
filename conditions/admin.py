"""Centro de control. Responsable: persona 3.

PENDIENTE: registrad aquí el modelo de incidencias. La primera versión del
centro de control puede ser directamente /admin/ (crear, activar y desactivar
incidencias); una pantalla propia es una mejora posterior.

Para entrar en /admin/ hace falta un usuario:
    python manage.py createsuperuser
"""

from django.contrib import admin
from .models import NetworkIncident

@admin.register(NetworkIncident)
class NetworkIncident(admin.ModelAdmin):
    list_display = ("description", "kind", "station_id", "line_id", "extra_minutes",
                    "is_active", "created_at",)
    
    list_filter = ("is_active", "kind", "line_id")
    list_editable = ("is_active",)
    search_fields = ("description", "station_id", "line_id")