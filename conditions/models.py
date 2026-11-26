"""Modelos de condiciones. Responsable: persona 3.

PENDIENTE: un modelo para las incidencias que se crean desde el centro de
control. Campos que exige el contrato (core.contracts.Incident): tipo,
estación, línea, minutos extra y descripción. Os conviene añadir además si
está activa y cuándo se creó.

Al crear o cambiar modelos:
    python manage.py makemigrations conditions
    python manage.py migrate
y subid al repositorio la carpeta conditions/migrations/.
"""
from django.core.exceptions import ValidationError
from django.db import models
from core.contracts import IncidentKind

LINE_CHOICES = [
    ("L1", "Línea 1 (Talleres - Exposición)"),
    ("L2", "Línea 2 (Sendero - General I. Zaragoza)"),
    ("L3", "Línea 3 (Hospital Metropolitano - General I. Zaragoza)"),
]

STATION_CHOICES = [
    #ESTACIONES DE LA LINEA 1
    ("talleres", "Talleres (L1)"),
    ("san-bernabe", "San Bernabé (L1)"),
    ("unidad-modelo", "Unidad Modelo (L1)"),
    ("aztlan", "Aztlán (L1)"),
    ("penitenciaria", "Penitenciaría (L1)"),
    ("alfonso-reyes", "Alfonso Reyes (L1)"),
    ("mitras", "Mitras (L1)"),
    ("simon-bolivar", "Simón Bolívar (L1)"),
    ("hospital", "Hospital (L1)"),
    ("edison", "Edison (L1)"),
    ("central", "Central (L1)"),
    ("cuauhtemoc", "Cuauhtémoc (L1 / L2)"),
    ("del-golfo", "Del Golfo (L1)"),
    ("felix-u-gomez", "Félix U. Gómez (L1 / L3)"),
    ("parque-fundidora", "Parque Fundidora (L1)"),
    ("y-griega", "Y Griega (L1)"),
    ("eloy-cavazos", "Eloy Cavazos (L1)"),
    ("lerdo-de-tejada", "Lerdo de Tejada (L1)"),
    ("exposicion", "Exposición (L1)"),

    #ESTACIONES DE LA LINEA 2
    ("sendero", "Sendero (L2)"),
    ("santiago-tapia", "Santiago Tapia (L2)"),
    ("san-nicolas", "San Nicolás (L2)"),
    ("anahuac", "Anáhuac (L2)"),
    ("universidad", "Universidad (L2)"),
    ("ninos-heroes", "Niños Héroes (L2)"),
    ("regina", "Regina (L2)"),
    ("general-anaya", "General Anaya (L2)"),
    ("alameda", "Alameda (L2)"),
    ("fundadores", "Fundadores (L2)"),
    ("padre-mier", "Padre Mier (L2)"),
    ("general-i-zaragoza", "General I. Zaragoza (L2 / L3)"),
    #ESTACIONES LINEA 3
    ("hospital-metropolitano", "Hospital Metropolitano (L3)"),
    ("los-angeles", "Los Ángeles (L3)"),
    ("ruiz-cortines", "Ruiz Cortines (L3)"),
    ("colonia-moderna", "Colonia Moderna (L3)"),
    ("metalurgicos", "Metalúrgicos (L3)"),
    ("colonia-obrera", "Colonia Obrera (L3)"),
    ("santa-lucia", "Santa Lucía (L3)"),
]

class NetworkIncident(models.Model):
    """Incidencia ha sido registrada desde el centro de control (/admin/)."""

    KIND_CHOICES = [
        (IncidentKind.STATION_CLOSED.value, "Estación cerrada"),
        (IncidentKind.LINE_DELAY.value, "Retraso en línea"),
    ]

    kind = models.CharField( "Tipo de incidencia", max_length=20, choices=KIND_CHOICES,)
    station_id = models.CharField("Estación afectada", max_length=50, choices=STATION_CHOICES,
                                blank=True, null=True, help_text="Obligatorio si el tipo es 'Estación cerrada'.",)
    line_id = models.CharField("Linea afectada", max_length=5, choices=LINE_CHOICES, 
                                blank=True, null=True, help_text="Obligatorio si el tipo es 'Retraso en línea'.",)
    extra_minutes = models.FloatField("Minutos extra de retraso", default=0.0, help_text="Penalización en minutos (0 si es cierre de estación).",)
    description = models.CharField("Descripción pública", max_length=255, help_text="Texto que verá el usuario en el planificador.",)
    is_active = models.BooleanField("Activa", default=True, help_text="Desmarca esta casilla para mantenerla preparada sin que afecte a las rutas.",)
    created_at = models.DateTimeField("Fecha de creación", auto_now_add=True)

    class Meta:
        verbose_name = "Incidencia"
        verbose_name_plural = "Incidencias"
        ordering = ["-created_at"]

    def clean(self):
        """Valida coherencia entre tipo de incidencia y estación/línea."""
        if self.kind == IncidentKind.STATION_CLOSED.value and not self.station_id:
            raise ValidationError({"station_id": "Debes seleccionar una estación cuando está cerrada."})
        if self.kind == IncidentKind.LINE_DELAY.value and not self.line_id:
            raise ValidationError({"line_id": "Debes seleccionar una línea cuando hay retraso."})
        if self.extra_minutes < 0:
            raise ValidationError({"extra_minutes": "Los minutos extra no pueden ser negativos."})

    def __str__(self) -> str: 
        target = self.station_id or self.line_id or "Red"
        estado = "ACTIVA" if self.is_active else "Inactiva"
        return f"[{estado}] {self.get_kind_display()} - {target}: {self.description}"