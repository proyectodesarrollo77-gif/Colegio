"""Control de asistencia e inasistencias."""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class AttendanceSession(BaseModel):
    """Sesion de clase sobre la que se toma asistencia."""

    assignment = models.ForeignKey(
        "teachers.TeachingAssignment", verbose_name="Asignacion", on_delete=models.CASCADE, related_name="attendance_sessions"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="attendance_sessions"
    )
    date = models.DateField("Fecha", default=timezone.localdate, db_index=True)
    block = models.PositiveSmallIntegerField("Bloque / hora", default=1)
    topic = models.CharField("Tema de la clase", max_length=240, blank=True)
    is_closed = models.BooleanField("Cerrada", default=False)
    taken_by = models.ForeignKey(
        "users.User", verbose_name="Registrada por", null=True, blank=True, on_delete=models.SET_NULL, related_name="attendance_sessions"
    )

    class Meta:
        db_table = "attendance_session"
        verbose_name = "Sesion de asistencia"
        verbose_name_plural = "Sesiones de asistencia"
        unique_together = ("assignment", "date", "block")
        ordering = ["-date", "block"]

    def __str__(self):
        return f"{self.assignment} - {self.date}"

    @property
    def summary(self):
        return {
            status: self.records.filter(status=status).count()
            for status, _ in AttendanceRecord.STATUS_CHOICES
        }


class AttendanceRecord(BaseModel):
    STATUS_CHOICES = [
        ("PRESENTE", "Presente"),
        ("AUSENTE", "Ausente"),
        ("TARDE", "Llegada tarde"),
        ("EXCUSA", "Ausencia justificada"),
        ("RETIRO", "Retiro anticipado"),
    ]

    session = models.ForeignKey(
        AttendanceSession, verbose_name="Sesion", on_delete=models.CASCADE, related_name="records"
    )
    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="attendance_records"
    )
    status = models.CharField("Estado", max_length=10, choices=STATUS_CHOICES, default="PRESENTE", db_index=True)
    minutes_late = models.PositiveSmallIntegerField("Minutos de retraso", default=0)
    excuse_document = models.FileField("Excusa", upload_to="attendance/excuses/%Y/%m/", null=True, blank=True)
    observation = models.CharField("Observacion", max_length=240, blank=True)

    class Meta:
        db_table = "attendance_record"
        verbose_name = "Registro de asistencia"
        verbose_name_plural = "Registros de asistencia"
        unique_together = ("session", "student")
        ordering = ["student__last_name"]
        indexes = [models.Index(fields=["student", "status"])]

    def __str__(self):
        return f"{self.student} - {self.get_status_display()}"


class AttendanceSummary(BaseModel):
    """Consolidado de inasistencias por estudiante, asignatura y periodo."""

    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="attendance_summaries"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="attendance_summaries"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura", null=True, blank=True, on_delete=models.CASCADE, related_name="attendance_summaries"
    )
    total_sessions = models.PositiveSmallIntegerField("Sesiones totales", default=0)
    absences = models.PositiveSmallIntegerField("Inasistencias", default=0)
    justified = models.PositiveSmallIntegerField("Justificadas", default=0)
    late_arrivals = models.PositiveSmallIntegerField("Llegadas tarde", default=0)
    attendance_rate = models.DecimalField("Porcentaje de asistencia", max_digits=5, decimal_places=2, default=100)

    class Meta:
        db_table = "attendance_summary"
        verbose_name = "Consolidado de asistencia"
        verbose_name_plural = "Consolidados de asistencia"
        unique_together = ("student", "period", "subject")
        ordering = ["student__last_name", "subject__name"]

    def __str__(self):
        return f"{self.student} - {self.period}: {self.attendance_rate}%"
