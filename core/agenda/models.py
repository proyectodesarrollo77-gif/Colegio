"""
Agenda virtual: calendario institucional, actividades y circulares.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class AgendaEvent(BaseModel):
    """Evento del calendario institucional."""

    TYPE_CHOICES = [
        ("ACADEMICO", "Academico"),
        ("INSTITUCIONAL", "Institucional"),
        ("CULTURAL", "Cultural"),
        ("DEPORTIVO", "Deportivo"),
        ("REUNION", "Reunion"),
        ("EVALUACION", "Evaluacion"),
        ("FESTIVO", "Festivo"),
        ("ENTREGA_BOLETINES", "Entrega de boletines"),
    ]
    AUDIENCE_CHOICES = [
        ("TODOS", "Toda la comunidad"),
        ("ESTUDIANTES", "Estudiantes"),
        ("DOCENTES", "Docentes"),
        ("ACUDIENTES", "Acudientes"),
        ("DIRECTIVOS", "Directivos"),
        ("GRUPO", "Grupo especifico"),
    ]

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="agenda_events"
    )
    title = models.CharField("Titulo", max_length=200)
    description = models.TextField("Descripcion", blank=True)
    event_type = models.CharField("Tipo", max_length=20, choices=TYPE_CHOICES, default="ACADEMICO")
    audience = models.CharField("Dirigido a", max_length=12, choices=AUDIENCE_CHOICES, default="TODOS")
    groups = models.ManyToManyField(
        "academic.Group", verbose_name="Grupos", blank=True, related_name="agenda_events"
    )
    start_at = models.DateTimeField("Inicio", db_index=True)
    end_at = models.DateTimeField("Fin", null=True, blank=True)
    all_day = models.BooleanField("Todo el dia", default=False)
    place = models.CharField("Lugar", max_length=160, blank=True)
    color = models.CharField("Color", max_length=20, default="#4F46E5")
    is_published = models.BooleanField("Publicado", default=True)
    send_notification = models.BooleanField("Notificar", default=False)
    attachment = models.FileField("Anexo", upload_to="agenda/%Y/%m/", null=True, blank=True)

    class Meta:
        db_table = "agenda_event"
        verbose_name = "Evento de agenda"
        verbose_name_plural = "Agenda institucional"
        ordering = ["start_at"]
        indexes = [models.Index(fields=["start_at", "is_published"])]

    def __str__(self):
        return f"{self.title} ({self.start_at:%Y-%m-%d})"


class AgendaActivity(BaseModel):
    """Actividad academica asignada a un grupo (tareas, talleres, entregas)."""

    STATUS_CHOICES = [
        ("PROGRAMADA", "Programada"),
        ("EN_CURSO", "En curso"),
        ("FINALIZADA", "Finalizada"),
        ("CANCELADA", "Cancelada"),
    ]

    assignment = models.ForeignKey(
        "teachers.TeachingAssignment", verbose_name="Asignacion", null=True, blank=True, on_delete=models.CASCADE, related_name="agenda_activities"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", on_delete=models.CASCADE, related_name="agenda_activities"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura", null=True, blank=True, on_delete=models.SET_NULL, related_name="agenda_activities"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", null=True, blank=True, on_delete=models.SET_NULL, related_name="agenda_activities"
    )
    title = models.CharField("Titulo", max_length=200)
    description = models.TextField("Descripcion", blank=True)
    assigned_date = models.DateField("Fecha de asignacion", default=timezone.localdate)
    due_date = models.DateField("Fecha de entrega", null=True, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PROGRAMADA")
    attachment = models.FileField("Material", upload_to="agenda/activities/%Y/%m/", null=True, blank=True)
    notify_guardians = models.BooleanField("Notificar acudientes", default=True)

    class Meta:
        db_table = "agenda_activity"
        verbose_name = "Actividad de agenda"
        verbose_name_plural = "Actividades de agenda"
        ordering = ["-assigned_date"]

    def __str__(self):
        return f"{self.title} - {self.group}"


class Circular(BaseModel):
    """Comunicado o circular institucional enviado por correo y plataforma."""

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("PROGRAMADA", "Programada"),
        ("ENVIADA", "Enviada"),
        ("CANCELADA", "Cancelada"),
    ]

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="circulars"
    )
    number = models.CharField("Numero", max_length=24, blank=True)
    subject = models.CharField("Asunto", max_length=200)
    body = models.TextField("Contenido")
    audience = models.CharField(
        "Dirigido a",
        max_length=12,
        choices=[
            ("TODOS", "Toda la comunidad"),
            ("ESTUDIANTES", "Estudiantes"),
            ("DOCENTES", "Docentes"),
            ("ACUDIENTES", "Acudientes"),
            ("GRUPO", "Grupos seleccionados"),
        ],
        default="TODOS",
    )
    groups = models.ManyToManyField("academic.Group", verbose_name="Grupos", blank=True, related_name="circulars")
    attachment = models.FileField("Anexo", upload_to="agenda/circulars/%Y/%m/", null=True, blank=True)
    scheduled_at = models.DateTimeField("Programada para", null=True, blank=True)
    sent_at = models.DateTimeField("Enviada el", null=True, blank=True)
    recipients_count = models.PositiveIntegerField("Destinatarios", default=0)
    opened_count = models.PositiveIntegerField("Aperturas", default=0)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="BORRADOR")
    send_email = models.BooleanField("Enviar por correo", default=True)

    class Meta:
        db_table = "agenda_circular"
        verbose_name = "Circular"
        verbose_name_plural = "Circulares"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} {self.subject}".strip()
