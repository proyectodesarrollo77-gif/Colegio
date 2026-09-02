"""
Reportes academicos, estadisticos y administrativos.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class ReportDefinition(BaseModel):
    """Catalogo de reportes disponibles en la plataforma."""

    CATEGORY_CHOICES = [
        ("ACADEMICO", "Academico"),
        ("ESTADISTICO", "Estadistico"),
        ("ADMINISTRATIVO", "Administrativo"),
        ("CONVIVENCIA", "Convivencia"),
        ("ASISTENCIA", "Asistencia"),
    ]
    OUTPUT_CHOICES = [("PDF", "PDF"), ("XLSX", "Excel"), ("CSV", "CSV"), ("HTML", "Pantalla")]

    code = models.CharField("Codigo", max_length=48, unique=True)
    name = models.CharField("Nombre del reporte", max_length=180)
    category = models.CharField("Categoria", max_length=16, choices=CATEGORY_CHOICES, default="ACADEMICO")
    description = models.TextField("Descripcion", blank=True)
    icon = models.CharField("Icono", max_length=40, default="bar-chart")
    parameters = models.JSONField("Parametros", default=list, blank=True)
    default_output = models.CharField("Formato por defecto", max_length=6, choices=OUTPUT_CHOICES, default="PDF")
    allowed_outputs = models.JSONField("Formatos permitidos", default=list, blank=True)
    required_module = models.CharField("Modulo requerido", max_length=80, default="reports.academic")
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "report_definition"
        verbose_name = "Reporte"
        verbose_name_plural = "Catalogo de reportes"
        ordering = ["category", "order", "name"]

    def __str__(self):
        return self.name


class ReportExecution(BaseModel):
    """Historial de ejecuciones y descargas de reportes."""

    STATUS_CHOICES = [
        ("EN_PROCESO", "En proceso"),
        ("COMPLETADO", "Completado"),
        ("ERROR", "Con error"),
    ]

    definition = models.ForeignKey(
        ReportDefinition, verbose_name="Reporte", on_delete=models.CASCADE, related_name="executions"
    )
    executed_by = models.ForeignKey(
        "users.User", verbose_name="Ejecutado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="report_executions"
    )
    parameters = models.JSONField("Parametros usados", default=dict, blank=True)
    output_format = models.CharField("Formato", max_length=6, default="PDF")
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="EN_PROCESO")
    rows = models.PositiveIntegerField("Registros generados", default=0)
    duration_ms = models.PositiveIntegerField("Duracion (ms)", default=0)
    file = models.FileField("Archivo", upload_to="reports/exports/%Y/%m/", null=True, blank=True)
    error_message = models.CharField("Mensaje de error", max_length=320, blank=True)
    executed_at = models.DateTimeField("Ejecutado el", default=timezone.now)

    class Meta:
        db_table = "report_execution"
        verbose_name = "Ejecucion de reporte"
        verbose_name_plural = "Ejecuciones de reportes"
        ordering = ["-executed_at"]

    def __str__(self):
        return f"{self.definition} - {self.executed_at:%Y-%m-%d %H:%M}"


class DashboardIndicator(BaseModel):
    """Indicadores calculados que alimentan el dashboard institucional."""

    code = models.CharField("Codigo", max_length=48, unique=True)
    name = models.CharField("Indicador", max_length=160)
    value = models.DecimalField("Valor", max_digits=14, decimal_places=2, default=0)
    previous_value = models.DecimalField("Valor anterior", max_digits=14, decimal_places=2, default=0)
    unit = models.CharField("Unidad", max_length=20, blank=True)
    icon = models.CharField("Icono", max_length=40, default="activity")
    color = models.CharField("Color", max_length=20, default="#4F46E5")
    category = models.CharField("Categoria", max_length=40, default="General")
    calculated_at = models.DateTimeField("Calculado el", default=timezone.now)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "report_dashboard_indicator"
        verbose_name = "Indicador del dashboard"
        verbose_name_plural = "Indicadores del dashboard"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def variation(self):
        if not self.previous_value:
            return 0
        return round(float(self.value - self.previous_value) / float(self.previous_value) * 100, 1)
