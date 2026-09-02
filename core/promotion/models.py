"""
Promocion y boletin final: cierre academico, comision de evaluacion y boletines.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class ClosingProcess(BaseModel):
    """Cierre academico de un periodo o del ano lectivo."""

    STATUS_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("EN_PROCESO", "En proceso"),
        ("CONSOLIDADO", "Consolidado"),
        ("CERRADO", "Cerrado"),
        ("REABIERTO", "Reabierto"),
    ]
    SCOPE_CHOICES = [("PERIODO", "Cierre de periodo"), ("ANUAL", "Cierre anual")]

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="closings"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", null=True, blank=True, on_delete=models.CASCADE, related_name="closings"
    )
    scope = models.CharField("Alcance", max_length=10, choices=SCOPE_CHOICES, default="PERIODO")
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PENDIENTE")
    started_at = models.DateTimeField("Iniciado el", null=True, blank=True)
    finished_at = models.DateTimeField("Finalizado el", null=True, blank=True)
    processed_students = models.PositiveIntegerField("Estudiantes procesados", default=0)
    processed_grades = models.PositiveIntegerField("Notas consolidadas", default=0)
    log = models.TextField("Bitacora del proceso", blank=True)
    executed_by = models.ForeignKey(
        "users.User", verbose_name="Ejecutado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="closing_processes"
    )

    class Meta:
        db_table = "promotion_closing"
        verbose_name = "Cierre academico"
        verbose_name_plural = "Cierres academicos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_scope_display()} - {self.period or self.school_year}"


class PromotionResult(BaseModel):
    """Resultado de promocion de un estudiante al finalizar el ano lectivo."""

    RESULT_CHOICES = [
        ("PROMOVIDO", "Promovido"),
        ("PROMOVIDO_COMPROMISO", "Promovido con compromiso"),
        ("NO_PROMOVIDO", "No promovido"),
        ("PENDIENTE_RECUPERACION", "Pendiente de recuperacion"),
        ("GRADUADO", "Graduado"),
        ("RETIRADO", "Retirado"),
    ]

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="promotion_results"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="promotion_results"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", on_delete=models.PROTECT, related_name="promotion_results"
    )
    next_grade = models.ForeignKey(
        "academic.Grade", verbose_name="Grado siguiente", null=True, blank=True, on_delete=models.SET_NULL, related_name="promoted_students"
    )
    average = models.DecimalField("Promedio general", max_digits=5, decimal_places=2, default=Decimal("0.00"))
    failed_subjects = models.PositiveSmallIntegerField("Asignaturas perdidas", default=0)
    failed_areas = models.PositiveSmallIntegerField("Areas perdidas", default=0)
    absences = models.PositiveSmallIntegerField("Inasistencias", default=0)
    result = models.CharField("Resultado", max_length=24, choices=RESULT_CHOICES, default="PROMOVIDO", db_index=True)
    rank = models.PositiveSmallIntegerField("Puesto en el grupo", null=True, blank=True)
    honor_roll = models.BooleanField("Cuadro de honor", default=False)
    observations = models.TextField("Observaciones de la comision", blank=True)
    approved = models.BooleanField("Aprobado por la comision", default=False)
    approved_by = models.ForeignKey(
        "users.User", verbose_name="Aprobado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_promotions"
    )
    approved_at = models.DateTimeField("Aprobado el", null=True, blank=True)

    class Meta:
        db_table = "promotion_result"
        verbose_name = "Resultado de promocion"
        verbose_name_plural = "Promocion estudiantil"
        unique_together = ("student", "school_year")
        ordering = ["group__grade__order", "group__code", "-average"]

    def __str__(self):
        return f"{self.student} - {self.get_result_display()}"


class FinalReportCard(BaseModel):
    """Boletin final consolidado del estudiante."""

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="final_reports"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="final_reports"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", null=True, blank=True, on_delete=models.CASCADE, related_name="report_cards"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", on_delete=models.PROTECT, related_name="report_cards"
    )
    is_final = models.BooleanField("Boletin final", default=False)
    average = models.DecimalField("Promedio", max_digits=5, decimal_places=2, default=Decimal("0.00"))
    rank = models.PositiveSmallIntegerField("Puesto", null=True, blank=True)
    total_absences = models.PositiveSmallIntegerField("Total inasistencias", default=0)
    tutor_observation = models.TextField("Observacion del tutor", blank=True)
    generated_at = models.DateTimeField("Generado el", default=timezone.now)
    generated_by = models.ForeignKey(
        "users.User", verbose_name="Generado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="generated_reports"
    )
    published = models.BooleanField("Publicado", default=False)
    file = models.FileField("Archivo PDF", upload_to="reports/cards/%Y/", null=True, blank=True)
    snapshot = models.JSONField("Detalle consolidado", default=dict, blank=True)

    class Meta:
        db_table = "promotion_report_card"
        verbose_name = "Boletin"
        verbose_name_plural = "Boletines"
        unique_together = ("student", "school_year", "period", "is_final")
        ordering = ["group__grade__order", "student__last_name"]

    def __str__(self):
        label = "Final" if self.is_final else str(self.period)
        return f"Boletin {label} - {self.student}"


class EvaluationCommission(BaseModel):
    """Acta de la comision de evaluacion y promocion."""

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="commissions"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", null=True, blank=True, on_delete=models.SET_NULL, related_name="commissions"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", null=True, blank=True, on_delete=models.SET_NULL, related_name="commissions"
    )
    act_number = models.CharField("Numero de acta", max_length=32)
    date = models.DateField("Fecha", default=timezone.localdate)
    place = models.CharField("Lugar", max_length=120, blank=True)
    attendees = models.TextField("Asistentes", blank=True)
    agenda = models.TextField("Orden del dia", blank=True)
    decisions = models.TextField("Decisiones", blank=True)
    commitments = models.TextField("Compromisos", blank=True)
    closed = models.BooleanField("Acta cerrada", default=False)

    class Meta:
        db_table = "promotion_commission"
        verbose_name = "Comision de evaluacion"
        verbose_name_plural = "Comisiones de evaluacion"
        ordering = ["-date"]

    def __str__(self):
        return f"Acta {self.act_number} - {self.date}"
