"""
Aula virtual: cursos, material academico, actividades y seguimiento.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class Course(BaseModel):
    """Curso virtual asociado a una asignacion academica."""

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("PUBLICADO", "Publicado"),
        ("ARCHIVADO", "Archivado"),
    ]

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="courses"
    )
    assignment = models.ForeignKey(
        "teachers.TeachingAssignment", verbose_name="Asignacion", null=True, blank=True, on_delete=models.SET_NULL, related_name="courses"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura", on_delete=models.CASCADE, related_name="courses"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", on_delete=models.CASCADE, related_name="courses"
    )
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente", null=True, blank=True, on_delete=models.SET_NULL, related_name="courses"
    )
    title = models.CharField("Titulo del curso", max_length=200)
    summary = models.TextField("Descripcion", blank=True)
    cover = models.ImageField("Portada", upload_to="classroom/covers/", null=True, blank=True)
    color = models.CharField("Color", max_length=20, default="#6366F1")
    status = models.CharField("Estado", max_length=10, choices=STATUS_CHOICES, default="BORRADOR")
    allow_submissions = models.BooleanField("Permite entregas", default=True)

    class Meta:
        db_table = "classroom_course"
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        unique_together = ("school_year", "subject", "group")
        ordering = ["group__grade__order", "subject__name"]

    def __str__(self):
        return f"{self.title} - {self.group}"


class CourseUnit(BaseModel):
    """Unidad o modulo del curso."""

    course = models.ForeignKey(Course, verbose_name="Curso", on_delete=models.CASCADE, related_name="units")
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", null=True, blank=True, on_delete=models.SET_NULL, related_name="course_units"
    )
    title = models.CharField("Titulo", max_length=180)
    description = models.TextField("Descripcion", blank=True)
    order = models.PositiveSmallIntegerField("Orden", default=0)
    is_published = models.BooleanField("Publicada", default=True)

    class Meta:
        db_table = "classroom_unit"
        verbose_name = "Unidad del curso"
        verbose_name_plural = "Unidades del curso"
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class CourseMaterial(BaseModel):
    """Material academico: documentos, enlaces y videos."""

    KIND_CHOICES = [
        ("DOCUMENTO", "Documento"),
        ("PRESENTACION", "Presentacion"),
        ("VIDEO", "Video"),
        ("ENLACE", "Enlace externo"),
        ("GUIA", "Guia de trabajo"),
        ("LECTURA", "Lectura"),
    ]

    course = models.ForeignKey(Course, verbose_name="Curso", on_delete=models.CASCADE, related_name="materials")
    unit = models.ForeignKey(
        CourseUnit, verbose_name="Unidad", null=True, blank=True, on_delete=models.SET_NULL, related_name="materials"
    )
    title = models.CharField("Titulo", max_length=200)
    description = models.TextField("Descripcion", blank=True)
    kind = models.CharField("Tipo", max_length=14, choices=KIND_CHOICES, default="DOCUMENTO")
    file = models.FileField("Archivo", upload_to="classroom/materials/%Y/%m/", null=True, blank=True)
    url = models.URLField("Enlace", blank=True)
    published_at = models.DateTimeField("Publicado el", default=timezone.now)
    downloads = models.PositiveIntegerField("Descargas", default=0)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "classroom_material"
        verbose_name = "Material academico"
        verbose_name_plural = "Materiales academicos"
        ordering = ["order", "-published_at"]

    def __str__(self):
        return self.title


class CourseActivity(BaseModel):
    """Actividad evaluable del aula virtual."""

    KIND_CHOICES = [
        ("TAREA", "Tarea"),
        ("TALLER", "Taller"),
        ("QUIZ", "Quiz"),
        ("PROYECTO", "Proyecto"),
        ("FORO", "Foro"),
        ("EXPOSICION", "Exposicion"),
    ]
    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("PUBLICADA", "Publicada"),
        ("CERRADA", "Cerrada"),
        ("CALIFICADA", "Calificada"),
    ]

    course = models.ForeignKey(Course, verbose_name="Curso", on_delete=models.CASCADE, related_name="activities")
    unit = models.ForeignKey(
        CourseUnit, verbose_name="Unidad", null=True, blank=True, on_delete=models.SET_NULL, related_name="activities"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", null=True, blank=True, on_delete=models.SET_NULL, related_name="course_activities"
    )
    process = models.ForeignKey(
        "teachers.TeacherAcademicProcess",
        verbose_name="Proceso academico",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="course_activities",
    )
    title = models.CharField("Titulo", max_length=200)
    instructions = models.TextField("Instrucciones", blank=True)
    kind = models.CharField("Tipo", max_length=12, choices=KIND_CHOICES, default="TAREA")
    attachment = models.FileField("Material anexo", upload_to="classroom/activities/%Y/%m/", null=True, blank=True)
    max_score = models.DecimalField("Nota maxima", max_digits=5, decimal_places=2, default=Decimal("5.00"))
    weight = models.DecimalField("Porcentaje (%)", max_digits=5, decimal_places=2, default=Decimal("100.00"))
    opens_at = models.DateTimeField("Disponible desde", default=timezone.now)
    due_at = models.DateTimeField("Entrega hasta", null=True, blank=True)
    allow_late = models.BooleanField("Permite entrega tardia", default=False)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="BORRADOR")

    class Meta:
        db_table = "classroom_activity"
        verbose_name = "Actividad del aula"
        verbose_name_plural = "Actividades del aula"
        ordering = ["-opens_at"]

    def __str__(self):
        return f"{self.title} - {self.course}"

    @property
    def is_open(self):
        now = timezone.now()
        if self.status != "PUBLICADA":
            return False
        if self.due_at and now > self.due_at and not self.allow_late:
            return False
        return now >= self.opens_at


class ActivitySubmission(BaseModel):
    """Entrega del estudiante para una actividad del aula virtual."""

    STATUS_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("ENTREGADA", "Entregada"),
        ("TARDE", "Entregada tarde"),
        ("CALIFICADA", "Calificada"),
        ("NO_ENTREGADA", "No entregada"),
    ]

    activity = models.ForeignKey(
        CourseActivity, verbose_name="Actividad", on_delete=models.CASCADE, related_name="submissions"
    )
    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="activity_submissions"
    )
    content = models.TextField("Respuesta", blank=True)
    file = models.FileField("Archivo", upload_to="classroom/submissions/%Y/%m/", null=True, blank=True)
    submitted_at = models.DateTimeField("Entregada el", null=True, blank=True)
    status = models.CharField("Estado", max_length=14, choices=STATUS_CHOICES, default="PENDIENTE")
    score = models.DecimalField("Nota", max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField("Retroalimentacion", blank=True)
    graded_at = models.DateTimeField("Calificada el", null=True, blank=True)
    graded_by = models.ForeignKey(
        "users.User", verbose_name="Calificada por", null=True, blank=True, on_delete=models.SET_NULL, related_name="graded_submissions"
    )

    class Meta:
        db_table = "classroom_submission"
        verbose_name = "Entrega"
        verbose_name_plural = "Entregas"
        unique_together = ("activity", "student")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.activity}"

    def submit(self):
        self.submitted_at = timezone.now()
        due = self.activity.due_at
        self.status = "TARDE" if due and self.submitted_at > due else "ENTREGADA"
        self.save(update_fields=["submitted_at", "status"])


class CourseProgress(BaseModel):
    """Seguimiento consolidado del estudiante en el curso."""

    course = models.ForeignKey(Course, verbose_name="Curso", on_delete=models.CASCADE, related_name="progress_records")
    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="course_progress"
    )
    activities_total = models.PositiveSmallIntegerField("Actividades totales", default=0)
    activities_done = models.PositiveSmallIntegerField("Actividades entregadas", default=0)
    average_score = models.DecimalField("Promedio", max_digits=5, decimal_places=2, default=Decimal("0.00"))
    last_access = models.DateTimeField("Ultimo acceso", null=True, blank=True)

    class Meta:
        db_table = "classroom_progress"
        verbose_name = "Progreso del curso"
        verbose_name_plural = "Seguimiento del aula virtual"
        unique_together = ("course", "student")
        ordering = ["student__last_name"]

    def __str__(self):
        return f"{self.student} - {self.course}"

    @property
    def completion(self):
        if not self.activities_total:
            return 0
        return round(self.activities_done / self.activities_total * 100)
