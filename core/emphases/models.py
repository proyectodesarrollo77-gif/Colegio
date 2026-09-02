"""
Enfasis y disciplinas: apertura de grupos, asignacion docente y matriculas.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel, CatalogModel


class Emphasis(CatalogModel):
    """Enfasis, disciplina o electiva ofertada por la institucion."""

    KIND_CHOICES = [
        ("DEPORTIVO", "Deportivo"),
        ("ARTISTICO", "Artistico"),
        ("TECNICO", "Tecnico"),
        ("ACADEMICO", "Academico"),
        ("CULTURAL", "Cultural"),
        ("TECNOLOGICO", "Tecnologico"),
    ]

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="emphases"
    )
    kind = models.CharField("Tipo", max_length=14, choices=KIND_CHOICES, default="ACADEMICO")
    image = models.ImageField("Imagen", upload_to="emphases/", null=True, blank=True)
    color = models.CharField("Color", max_length=20, default="#0EA5E9")
    requirements = models.TextField("Requisitos", blank=True)

    class Meta:
        db_table = "emphasis"
        verbose_name = "Enfasis"
        verbose_name_plural = "Enfasis y disciplinas"
        unique_together = ("institution", "code")
        ordering = ["order", "name"]


class EmphasisGroup(BaseModel):
    """Apertura de un grupo de enfasis para un ano lectivo."""

    STATUS_CHOICES = [
        ("PLANEADO", "Planeado"),
        ("ABIERTO", "Abierto"),
        ("CERRADO", "Cerrado"),
        ("CANCELADO", "Cancelado"),
    ]

    emphasis = models.ForeignKey(
        Emphasis, verbose_name="Enfasis", on_delete=models.CASCADE, related_name="groups"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="emphasis_groups"
    )
    code = models.CharField("Codigo del grupo", max_length=24)
    name = models.CharField("Nombre del grupo", max_length=120)
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente asignado", null=True, blank=True, on_delete=models.SET_NULL, related_name="emphasis_groups"
    )
    grades = models.ManyToManyField(
        "academic.Grade", verbose_name="Grados habilitados", blank=True, related_name="emphasis_groups"
    )
    capacity = models.PositiveSmallIntegerField("Cupos", default=25)
    weekday = models.PositiveSmallIntegerField("Dia", default=1)
    start_time = models.TimeField("Hora de inicio", null=True, blank=True)
    end_time = models.TimeField("Hora de fin", null=True, blank=True)
    place = models.CharField("Lugar", max_length=120, blank=True)
    status = models.CharField("Estado", max_length=10, choices=STATUS_CHOICES, default="PLANEADO")

    class Meta:
        db_table = "emphasis_group"
        verbose_name = "Grupo de enfasis"
        verbose_name_plural = "Grupos de enfasis"
        unique_together = ("emphasis", "school_year", "code")
        ordering = ["emphasis__name", "code"]

    def __str__(self):
        return f"{self.emphasis} - {self.name}"

    @property
    def enrolled_count(self):
        return self.enrollments.filter(status="ACTIVA", deleted_at__isnull=True).count()

    @property
    def available_seats(self):
        return max(self.capacity - self.enrolled_count, 0)


class EmphasisEnrollment(BaseModel):
    STATUS_CHOICES = [
        ("ACTIVA", "Activa"),
        ("RETIRADA", "Retirada"),
        ("LISTA_ESPERA", "Lista de espera"),
        ("FINALIZADA", "Finalizada"),
    ]

    group = models.ForeignKey(
        EmphasisGroup, verbose_name="Grupo de enfasis", on_delete=models.CASCADE, related_name="enrollments"
    )
    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="emphasis_enrollments"
    )
    enrolled_at = models.DateField("Fecha de inscripcion", default=timezone.localdate)
    status = models.CharField("Estado", max_length=14, choices=STATUS_CHOICES, default="ACTIVA")
    priority = models.PositiveSmallIntegerField("Prioridad", default=1)
    score = models.DecimalField("Valoracion", max_digits=5, decimal_places=2, null=True, blank=True)
    observation = models.CharField("Observacion", max_length=240, blank=True)

    class Meta:
        db_table = "emphasis_enrollment"
        verbose_name = "Matricula de enfasis"
        verbose_name_plural = "Matriculas de enfasis"
        unique_together = ("group", "student")
        ordering = ["group__code", "student__last_name"]

    def __str__(self):
        return f"{self.student} - {self.group}"
