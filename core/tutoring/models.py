"""
Tutoria: acompanamiento, juicios de tutoria, convivencia y bloqueo de boletin.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class Tutor(BaseModel):
    """Docente tutor asignado a un grupo en un ano lectivo."""

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="tutors"
    )
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente tutor", on_delete=models.CASCADE, related_name="tutorships"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", on_delete=models.CASCADE, related_name="tutors"
    )
    start_date = models.DateField("Desde", default=timezone.localdate)
    end_date = models.DateField("Hasta", null=True, blank=True)
    is_main = models.BooleanField("Tutor principal", default=True)
    notes = models.CharField("Observaciones", max_length=240, blank=True)

    class Meta:
        db_table = "tutoring_tutor"
        verbose_name = "Tutor"
        verbose_name_plural = "Tutores"
        unique_together = ("school_year", "group", "teacher")
        ordering = ["group__grade__order", "group__code"]

    def __str__(self):
        return f"{self.teacher} - {self.group}"


class TutoringJudgment(BaseModel):
    """Juicio de tutoria emitido sobre un estudiante en un periodo."""

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="tutoring_judgments"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="tutoring_judgments"
    )
    tutor = models.ForeignKey(
        Tutor, verbose_name="Tutor", null=True, blank=True, on_delete=models.SET_NULL, related_name="judgments"
    )
    performance = models.ForeignKey(
        "academic.GradingScaleLevel",
        verbose_name="Desempeno global",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tutoring_judgments",
    )
    strengths = models.TextField("Fortalezas", blank=True)
    difficulties = models.TextField("Dificultades", blank=True)
    recommendations = models.TextField("Recomendaciones", blank=True)
    commitment = models.TextField("Compromisos", blank=True)
    published = models.BooleanField("Publicado en el boletin", default=False)

    class Meta:
        db_table = "tutoring_judgment"
        verbose_name = "Juicio de tutoria"
        verbose_name_plural = "Juicios de tutoria"
        unique_together = ("student", "period")
        ordering = ["student__last_name"]

    def __str__(self):
        return f"Tutoria {self.student} - {self.period}"


class CoexistenceEvaluation(BaseModel):
    """Valoracion de items de convivencia por estudiante y periodo."""

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="coexistence_evaluations"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="coexistence_evaluations"
    )
    item = models.ForeignKey(
        "academic.CoexistenceItem", verbose_name="Item de convivencia", on_delete=models.CASCADE, related_name="evaluations"
    )
    score = models.DecimalField("Valoracion", max_digits=5, decimal_places=2, null=True, blank=True)
    performance = models.ForeignKey(
        "academic.GradingScaleLevel",
        verbose_name="Desempeno",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="coexistence_evaluations",
    )
    observation = models.CharField("Observacion", max_length=240, blank=True)
    evaluated_by = models.ForeignKey(
        "users.User", verbose_name="Evaluado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="coexistence_evaluations"
    )

    class Meta:
        db_table = "tutoring_coexistence_evaluation"
        verbose_name = "Valoracion de convivencia"
        verbose_name_plural = "Valoraciones de convivencia"
        unique_together = ("student", "period", "item")
        ordering = ["item__order"]

    def __str__(self):
        return f"{self.student} / {self.item}"

    def save(self, *args, **kwargs):
        """El desempeno se deriva de la valoracion, no se digita aparte."""
        from core.academic.models import resolve_performance

        if self.period_id and self.score is not None:
            self.performance = resolve_performance(self.period.school_year, self.score)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"performance"}
        super().save(*args, **kwargs)


class ReportCardBlock(BaseModel):
    """Bloqueo de boletin por cartera, disciplina o documentacion pendiente."""

    REASON_CHOICES = [
        ("CARTERA", "Cartera pendiente"),
        ("DOCUMENTOS", "Documentacion incompleta"),
        ("DISCIPLINA", "Situacion disciplinaria"),
        ("BIBLIOTECA", "Material pendiente"),
        ("OTRO", "Otro motivo"),
    ]

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="report_blocks"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="report_blocks"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", null=True, blank=True, on_delete=models.CASCADE, related_name="report_blocks"
    )
    reason = models.CharField("Motivo", max_length=12, choices=REASON_CHOICES, default="CARTERA")
    detail = models.CharField("Detalle", max_length=240, blank=True)
    amount = models.DecimalField("Valor adeudado", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    blocked = models.BooleanField("Boletin bloqueado", default=True)
    released_at = models.DateTimeField("Liberado el", null=True, blank=True)
    released_by = models.ForeignKey(
        "users.User", verbose_name="Liberado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="released_report_blocks"
    )

    class Meta:
        db_table = "tutoring_report_block"
        verbose_name = "Bloqueo de boletin"
        verbose_name_plural = "Bloqueos de boletin"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} - {self.get_reason_display()}"

    def release(self, user=None):
        self.blocked = False
        self.released_at = timezone.now()
        self.released_by = user
        self.save(update_fields=["blocked", "released_at", "released_by"])


class TutoringMeeting(BaseModel):
    """Citaciones y reuniones de acompanamiento con acudientes."""

    STATUS_CHOICES = [
        ("PROGRAMADA", "Programada"),
        ("REALIZADA", "Realizada"),
        ("CANCELADA", "Cancelada"),
        ("NO_ASISTIO", "No asistio"),
    ]

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="tutoring_meetings"
    )
    tutor = models.ForeignKey(
        Tutor, verbose_name="Tutor", null=True, blank=True, on_delete=models.SET_NULL, related_name="meetings"
    )
    scheduled_at = models.DateTimeField("Fecha y hora")
    place = models.CharField("Lugar", max_length=120, blank=True)
    subject = models.CharField("Asunto", max_length=200)
    agreements = models.TextField("Acuerdos", blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PROGRAMADA")
    guardian_attended = models.BooleanField("Asistio el acudiente", default=False)

    class Meta:
        db_table = "tutoring_meeting"
        verbose_name = "Citacion de tutoria"
        verbose_name_plural = "Citaciones de tutoria"
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"{self.student} - {self.scheduled_at:%Y-%m-%d %H:%M}"
