"""
Recuperaciones academicas, actividades complementarias y refuerzo bilingue.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class RecoveryPlan(BaseModel):
    """Plan de recuperacion o nivelacion de una asignatura."""

    TYPE_CHOICES = [
        ("PERIODO", "Recuperacion de periodo"),
        ("FINAL", "Recuperacion final"),
        ("NIVELACION", "Nivelacion"),
        ("HABILITACION", "Habilitacion"),
        ("BILINGUE", "Refuerzo bilingue"),
    ]
    STATUS_CHOICES = [
        ("PROGRAMADO", "Programado"),
        ("EN_CURSO", "En curso"),
        ("EVALUADO", "Evaluado"),
        ("CERRADO", "Cerrado"),
    ]

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="recovery_plans"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", null=True, blank=True, on_delete=models.CASCADE, related_name="recovery_plans"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura", on_delete=models.CASCADE, related_name="recovery_plans"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", null=True, blank=True, on_delete=models.CASCADE, related_name="recovery_plans"
    )
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente responsable", null=True, blank=True, on_delete=models.SET_NULL, related_name="recovery_plans"
    )
    plan_type = models.CharField("Tipo", max_length=12, choices=TYPE_CHOICES, default="PERIODO")
    name = models.CharField("Nombre del plan", max_length=180)
    description = models.TextField("Descripcion", blank=True)
    objectives = models.TextField("Objetivos", blank=True)
    start_date = models.DateField("Fecha de inicio", default=timezone.localdate)
    end_date = models.DateField("Fecha de finalizacion", null=True, blank=True)
    evaluation_date = models.DateTimeField("Fecha de evaluacion", null=True, blank=True)
    maximum_score = models.DecimalField("Nota maxima alcanzable", max_digits=5, decimal_places=2, default=Decimal("3.50"))
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PROGRAMADO")
    is_bilingual = models.BooleanField("Proceso bilingue", default=False)

    class Meta:
        db_table = "recovery_plan"
        verbose_name = "Plan de recuperacion"
        verbose_name_plural = "Planes de recuperacion"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} - {self.subject}"


class RecoveryActivity(BaseModel):
    """Actividad complementaria del plan de recuperacion."""

    plan = models.ForeignKey(
        RecoveryPlan, verbose_name="Plan", on_delete=models.CASCADE, related_name="activities"
    )
    name = models.CharField("Actividad", max_length=180)
    description = models.TextField("Descripcion", blank=True)
    weight = models.DecimalField("Porcentaje (%)", max_digits=5, decimal_places=2, default=Decimal("100.00"))
    due_date = models.DateField("Fecha de entrega", null=True, blank=True)
    resource = models.FileField("Material de apoyo", upload_to="recoveries/%Y/%m/", null=True, blank=True)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "recovery_activity"
        verbose_name = "Actividad complementaria"
        verbose_name_plural = "Actividades complementarias"
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class RecoveryEnrollment(BaseModel):
    """Estudiante inscrito en un plan de recuperacion."""

    STATUS_CHOICES = [
        ("INSCRITO", "Inscrito"),
        ("PRESENTO", "Presento"),
        ("NO_PRESENTO", "No presento"),
        ("APROBO", "Aprobo"),
        ("REPROBO", "Reprobo"),
    ]

    plan = models.ForeignKey(
        RecoveryPlan, verbose_name="Plan", on_delete=models.CASCADE, related_name="enrollments"
    )
    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="recovery_enrollments"
    )
    previous_score = models.DecimalField("Nota anterior", max_digits=5, decimal_places=2, null=True, blank=True)
    score = models.DecimalField("Nota obtenida", max_digits=5, decimal_places=2, null=True, blank=True)
    final_score = models.DecimalField("Nota definitiva", max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="INSCRITO")
    observation = models.TextField("Observacion", blank=True)
    evaluated_at = models.DateTimeField("Evaluado el", null=True, blank=True)
    evaluated_by = models.ForeignKey(
        "users.User", verbose_name="Evaluado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="evaluated_recoveries"
    )
    applied_to_grade = models.BooleanField("Aplicado al boletin", default=False)

    class Meta:
        db_table = "recovery_enrollment"
        verbose_name = "Inscripcion a recuperacion"
        verbose_name_plural = "Inscripciones a recuperacion"
        unique_together = ("plan", "student")
        ordering = ["student__last_name"]

    def __str__(self):
        return f"{self.student} - {self.plan}"

    def resolve(self):
        """Calcula la nota definitiva respetando el tope del plan y la nota previa."""
        maximum = self.plan.maximum_score
        obtained = self.score or Decimal("0.00")
        previous = self.previous_score or Decimal("0.00")
        self.final_score = max(min(obtained, maximum), previous)

        passing = (
            self.plan.school_year.grading_scales.filter(is_default=True)
            .values_list("passing", flat=True)
            .first()
            or Decimal("3.00")
        )
        self.status = "APROBO" if self.final_score >= passing else "REPROBO"
        self.evaluated_at = timezone.now()
        return self.final_score


class RecoveryActivitySubmission(BaseModel):
    """Entrega del estudiante para una actividad complementaria."""

    activity = models.ForeignKey(
        RecoveryActivity, verbose_name="Actividad", on_delete=models.CASCADE, related_name="submissions"
    )
    enrollment = models.ForeignKey(
        RecoveryEnrollment, verbose_name="Inscripcion", on_delete=models.CASCADE, related_name="submissions"
    )
    submitted_at = models.DateTimeField("Entregado el", default=timezone.now)
    file = models.FileField("Archivo", upload_to="recoveries/submissions/%Y/%m/", null=True, blank=True)
    comments = models.TextField("Comentarios", blank=True)
    score = models.DecimalField("Nota", max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField("Retroalimentacion", blank=True)

    class Meta:
        db_table = "recovery_submission"
        verbose_name = "Entrega de recuperacion"
        verbose_name_plural = "Entregas de recuperacion"
        unique_together = ("activity", "enrollment")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.enrollment.student} - {self.activity}"
