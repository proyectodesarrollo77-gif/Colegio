"""
Observador del estudiante: seguimiento disciplinario e historial.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel, CatalogModel


class ObservationCategory(CatalogModel):
    """Tipologia de la observacion segun el manual de convivencia."""

    SEVERITY_CHOICES = [
        ("TIPO_I", "Situacion tipo I - Leve"),
        ("TIPO_II", "Situacion tipo II - Grave"),
        ("TIPO_III", "Situacion tipo III - Gravisima"),
        ("POSITIVA", "Reconocimiento positivo"),
        ("ACADEMICA", "Seguimiento academico"),
        ("INFORMATIVA", "Informativa"),
    ]

    severity = models.CharField("Tipificacion", max_length=12, choices=SEVERITY_CHOICES, default="TIPO_I")
    color = models.CharField("Color", max_length=20, default="#F59E0B")
    requires_guardian = models.BooleanField("Requiere citacion de acudiente", default=False)
    requires_commitment = models.BooleanField("Requiere acta de compromiso", default=False)
    manual_article = models.CharField("Articulo del manual", max_length=80, blank=True)

    class Meta:
        db_table = "observer_category"
        verbose_name = "Tipo de observacion"
        verbose_name_plural = "Tipos de observacion"
        ordering = ["order", "name"]


class ObserverEntry(BaseModel):
    """Anotacion en el observador del estudiante."""

    STATUS_CHOICES = [
        ("ABIERTA", "Abierta"),
        ("EN_SEGUIMIENTO", "En seguimiento"),
        ("CERRADA", "Cerrada"),
        ("ANULADA", "Anulada"),
    ]

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="observer_entries"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="observer_entries"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", null=True, blank=True, on_delete=models.SET_NULL, related_name="observer_entries"
    )
    category = models.ForeignKey(
        ObservationCategory, verbose_name="Tipo", on_delete=models.PROTECT, related_name="entries"
    )
    date = models.DateField("Fecha del hecho", default=timezone.localdate, db_index=True)
    place = models.CharField("Lugar", max_length=120, blank=True)
    description = models.TextField("Descripcion de la situacion")
    student_version = models.TextField("Version del estudiante", blank=True)
    actions_taken = models.TextField("Acciones adoptadas", blank=True)
    commitments = models.TextField("Compromisos", blank=True)
    reported_by = models.ForeignKey(
        "users.User", verbose_name="Reportado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="observer_entries"
    )
    guardian_notified = models.BooleanField("Acudiente notificado", default=False)
    guardian_notified_at = models.DateTimeField("Notificado el", null=True, blank=True)
    student_signed = models.BooleanField("Firmado por el estudiante", default=False)
    guardian_signed = models.BooleanField("Firmado por el acudiente", default=False)
    status = models.CharField("Estado", max_length=16, choices=STATUS_CHOICES, default="ABIERTA")
    attachment = models.FileField("Anexo", upload_to="observer/%Y/%m/", null=True, blank=True)

    class Meta:
        db_table = "observer_entry"
        verbose_name = "Anotacion del observador"
        verbose_name_plural = "Observador"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["student", "-date"])]

    def __str__(self):
        return f"{self.student} - {self.category} ({self.date})"

    def notify_guardian(self):
        self.guardian_notified = True
        self.guardian_notified_at = timezone.now()
        self.save(update_fields=["guardian_notified", "guardian_notified_at"])


class ObserverFollowUp(BaseModel):
    """Seguimiento posterior a una anotacion."""

    entry = models.ForeignKey(
        ObserverEntry, verbose_name="Anotacion", on_delete=models.CASCADE, related_name="follow_ups"
    )
    date = models.DateField("Fecha", default=timezone.localdate)
    description = models.TextField("Seguimiento")
    result = models.CharField(
        "Resultado",
        max_length=16,
        choices=[("POSITIVO", "Positivo"), ("PARCIAL", "Parcial"), ("NEGATIVO", "Negativo"), ("PENDIENTE", "Pendiente")],
        default="PENDIENTE",
    )
    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable", null=True, blank=True, on_delete=models.SET_NULL, related_name="observer_follow_ups"
    )

    class Meta:
        db_table = "observer_follow_up"
        verbose_name = "Seguimiento"
        verbose_name_plural = "Seguimientos"
        ordering = ["-date"]

    def __str__(self):
        return f"Seguimiento {self.entry} - {self.date}"
