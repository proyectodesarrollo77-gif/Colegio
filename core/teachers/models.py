"""
Administracion docente: registro, asignaturas, horarios y carga academica.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel
from core.users.models import DOCUMENT_TYPES, GENDER_CHOICES

WEEKDAYS = [
    (1, "Lunes"),
    (2, "Martes"),
    (3, "Miercoles"),
    (4, "Jueves"),
    (5, "Viernes"),
    (6, "Sabado"),
    (7, "Domingo"),
]


class Teacher(BaseModel):
    CONTRACT_CHOICES = [
        ("PLANTA", "Planta"),
        ("PROVISIONAL", "Provisional"),
        ("CONTRATO", "Contrato"),
        ("CATEDRA", "Catedra"),
        ("HORA_CATEDRA", "Hora catedra"),
    ]
    STATUS_CHOICES = [
        ("ACTIVO", "Activo"),
        ("LICENCIA", "En licencia"),
        ("RETIRADO", "Retirado"),
        ("INACTIVO", "Inactivo"),
    ]

    user = models.OneToOneField(
        "users.User", verbose_name="Usuario de acceso", null=True, blank=True, on_delete=models.SET_NULL, related_name="teacher_profile"
    )
    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="teachers"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", null=True, blank=True, on_delete=models.SET_NULL, related_name="teachers"
    )

    teacher_code = models.CharField("Codigo docente", max_length=32, unique=True, db_index=True)
    document_type = models.CharField("Tipo de documento", max_length=8, choices=DOCUMENT_TYPES, default="CC")
    document_number = models.CharField("Numero de documento", max_length=32, unique=True, db_index=True)
    first_name = models.CharField("Nombres", max_length=120)
    last_name = models.CharField("Apellidos", max_length=120)
    gender = models.CharField("Genero", max_length=1, choices=GENDER_CHOICES, default="N")
    birth_date = models.DateField("Fecha de nacimiento", null=True, blank=True)
    photo = models.ImageField("Fotografia", upload_to="teachers/photos/", null=True, blank=True)

    email = models.EmailField("Correo institucional", blank=True)
    personal_email = models.EmailField("Correo personal", blank=True)
    phone = models.CharField("Telefono", max_length=32, blank=True)
    mobile = models.CharField("Celular", max_length=32, blank=True)
    address = models.CharField("Direccion", max_length=200, blank=True)

    profession = models.CharField("Profesion", max_length=160, blank=True)
    academic_title = models.CharField("Titulo academico", max_length=160, blank=True)
    specialization = models.CharField("Especializacion", max_length=160, blank=True)
    escalafon = models.CharField("Escalafon", max_length=40, blank=True)

    contract_type = models.CharField("Tipo de vinculacion", max_length=14, choices=CONTRACT_CHOICES, default="CONTRATO")
    hire_date = models.DateField("Fecha de vinculacion", null=True, blank=True)
    end_date = models.DateField("Fecha de retiro", null=True, blank=True)
    weekly_hours = models.PositiveSmallIntegerField("Horas semanales contratadas", default=22)
    status = models.CharField("Estado", max_length=10, choices=STATUS_CHOICES, default="ACTIVO", db_index=True)

    is_tutor = models.BooleanField("Puede ser tutor", default=False)
    is_coordinator = models.BooleanField("Es coordinador", default=False)
    signature = models.ImageField("Firma digitalizada", upload_to="teachers/signatures/", null=True, blank=True)
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "teacher"
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def assigned_hours(self):
        return (
            self.assignments.filter(is_active=True, deleted_at__isnull=True).aggregate(
                total=models.Sum("weekly_hours")
            )["total"]
            or 0
        )

    @property
    def load_percentage(self):
        return round(self.assigned_hours / self.weekly_hours * 100) if self.weekly_hours else 0

    def save(self, *args, **kwargs):
        if not self.teacher_code:
            count = Teacher.objects.count() + 1
            self.teacher_code = f"DOC{count:04d}"
        super().save(*args, **kwargs)


class TeachingAssignment(BaseModel):
    """Asignacion academica: docente + asignatura + grupo + periodo."""

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="teaching_assignments"
    )
    teacher = models.ForeignKey(
        Teacher, verbose_name="Docente", on_delete=models.CASCADE, related_name="assignments"
    )
    subject = models.ForeignKey(
        "academic.Subject", verbose_name="Asignatura", on_delete=models.CASCADE, related_name="assignments"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", on_delete=models.CASCADE, related_name="assignments"
    )
    weekly_hours = models.PositiveSmallIntegerField("Horas semanales", default=1)
    is_main = models.BooleanField("Docente titular", default=True)
    notes = models.CharField("Observaciones", max_length=240, blank=True)

    class Meta:
        db_table = "teacher_assignment"
        verbose_name = "Asignacion academica"
        verbose_name_plural = "Asignaciones academicas"
        unique_together = ("school_year", "teacher", "subject", "group")
        ordering = ["group__grade__order", "group__code", "subject__name"]

    def __str__(self):
        return f"{self.teacher} - {self.subject} - {self.group}"


class ScheduleSlot(BaseModel):
    """Franja horaria de una asignacion academica."""

    assignment = models.ForeignKey(
        TeachingAssignment, verbose_name="Asignacion", on_delete=models.CASCADE, related_name="schedule_slots"
    )
    weekday = models.PositiveSmallIntegerField("Dia", choices=WEEKDAYS)
    block = models.PositiveSmallIntegerField("Bloque / hora", default=1)
    start_time = models.TimeField("Hora de inicio")
    end_time = models.TimeField("Hora de finalizacion")
    classroom = models.CharField("Aula", max_length=40, blank=True)

    class Meta:
        db_table = "teacher_schedule_slot"
        verbose_name = "Franja de horario"
        verbose_name_plural = "Horarios"
        ordering = ["weekday", "start_time"]
        unique_together = ("assignment", "weekday", "block")

    def __str__(self):
        return f"{self.get_weekday_display()} {self.start_time:%H:%M} - {self.assignment.subject}"


class TeacherAcademicProcess(BaseModel):
    """Procesos academicos definidos por el docente para su asignatura."""

    assignment = models.ForeignKey(
        TeachingAssignment, verbose_name="Asignacion", on_delete=models.CASCADE, related_name="processes"
    )
    period = models.ForeignKey(
        "academic.AcademicPeriod", verbose_name="Periodo", on_delete=models.CASCADE, related_name="teacher_processes"
    )
    process = models.ForeignKey(
        "academic.AcademicProcess",
        verbose_name="Proceso",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="teacher_processes",
    )
    name = models.CharField("Nombre", max_length=160)
    description = models.TextField("Descripcion", blank=True)
    weight = models.DecimalField("Porcentaje (%)", max_digits=5, decimal_places=2, default=Decimal("100.00"))
    due_date = models.DateField("Fecha limite", null=True, blank=True)
    is_closed = models.BooleanField("Cerrado", default=False)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "teacher_academic_process"
        verbose_name = "Proceso academico del docente"
        verbose_name_plural = "Procesos academicos del docente"
        ordering = ["period__number", "order"]

    def __str__(self):
        return f"{self.name} - {self.assignment}"


class TeacherAbsence(BaseModel):
    """Novedades de ausencia o licencia docente."""

    KIND_CHOICES = [
        ("INCAPACIDAD", "Incapacidad"),
        ("PERMISO", "Permiso"),
        ("LICENCIA", "Licencia"),
        ("CAPACITACION", "Capacitacion"),
        ("OTRO", "Otro"),
    ]

    teacher = models.ForeignKey(Teacher, verbose_name="Docente", on_delete=models.CASCADE, related_name="absences")
    kind = models.CharField("Tipo", max_length=14, choices=KIND_CHOICES, default="PERMISO")
    start_date = models.DateField("Desde", default=timezone.localdate)
    end_date = models.DateField("Hasta", null=True, blank=True)
    reason = models.TextField("Motivo", blank=True)
    substitute = models.ForeignKey(
        Teacher, verbose_name="Docente suplente", null=True, blank=True, on_delete=models.SET_NULL, related_name="substitutions"
    )
    approved = models.BooleanField("Aprobada", default=False)
    approved_by = models.ForeignKey(
        "users.User", verbose_name="Aprobada por", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_absences"
    )
    approved_at = models.DateTimeField("Aprobada el", null=True, blank=True)

    class Meta:
        db_table = "teacher_absence"
        verbose_name = "Novedad docente"
        verbose_name_plural = "Novedades docentes"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.teacher} - {self.get_kind_display()}"
