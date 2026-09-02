"""Datos institucionales: institucion, sedes, jornadas y calendario."""
from __future__ import annotations

from django.db import models

from config.models_base import BaseModel, CatalogModel


class Institution(BaseModel):
    CALENDAR_CHOICES = [("A", "Calendario A"), ("B", "Calendario B"), ("C", "Calendario C")]
    NATURE_CHOICES = [("OFICIAL", "Oficial"), ("PRIVADA", "Privada"), ("MIXTA", "Mixta")]

    code = models.CharField("Codigo DANE", max_length=32, unique=True)
    name = models.CharField("Nombre de la institucion", max_length=200)
    short_name = models.CharField("Nombre corto", max_length=80, blank=True)
    nit = models.CharField("NIT", max_length=32, blank=True)
    resolution = models.CharField("Resolucion de aprobacion", max_length=200, blank=True)
    nature = models.CharField("Naturaleza", max_length=12, choices=NATURE_CHOICES, default="PRIVADA")
    calendar = models.CharField("Calendario", max_length=1, choices=CALENDAR_CHOICES, default="A")

    country = models.CharField("Pais", max_length=80, default="Colombia")
    department = models.CharField("Departamento", max_length=80, blank=True)
    city = models.CharField("Ciudad", max_length=80, blank=True)
    address = models.CharField("Direccion", max_length=200, blank=True)
    phone = models.CharField("Telefono", max_length=40, blank=True)
    email = models.EmailField("Correo institucional", blank=True)
    website = models.URLField("Sitio web", blank=True)

    logo = models.ImageField("Logotipo", upload_to="institution/", null=True, blank=True)
    seal = models.ImageField("Sello", upload_to="institution/", null=True, blank=True)
    rector_name = models.CharField("Nombre del rector", max_length=160, blank=True)
    rector_document = models.CharField("Documento del rector", max_length=32, blank=True)
    rector_signature = models.ImageField("Firma del rector", upload_to="institution/", null=True, blank=True)
    secretary_name = models.CharField("Nombre de secretaria", max_length=160, blank=True)
    secretary_signature = models.ImageField(
        "Firma de secretaria", upload_to="institution/", null=True, blank=True
    )

    motto = models.CharField("Lema", max_length=200, blank=True)
    mission = models.TextField("Mision", blank=True)
    vision = models.TextField("Vision", blank=True)
    primary_color = models.CharField("Color primario", max_length=20, default="#4F46E5")
    accent_color = models.CharField("Color de acento", max_length=20, default="#0EA5E9")
    is_default = models.BooleanField("Institucion principal", default=False)

    class Meta:
        db_table = "institution"
        verbose_name = "Institucion"
        verbose_name_plural = "Instituciones"
        ordering = ["name"]

    def __str__(self):
        return self.short_name or self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            Institution.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        """
        Institucion en la que se esta trabajando.

        Es la elegida al iniciar sesion; fuera de una peticion (comandos,
        tareas) cae en la institucion por defecto, que es el comportamiento
        de una instalacion con una sola institucion.
        """
        from .context import get_active_institution

        active = get_active_institution()
        if active is not None:
            return active
        return cls.objects.filter(is_active=True).order_by("-is_default", "id").first()


class Campus(BaseModel):
    """Sede fisica de la institucion."""

    institution = models.ForeignKey(
        Institution, verbose_name="Institucion", on_delete=models.CASCADE, related_name="campuses"
    )
    code = models.CharField("Codigo", max_length=32)
    name = models.CharField("Nombre de la sede", max_length=160)
    address = models.CharField("Direccion", max_length=200, blank=True)
    phone = models.CharField("Telefono", max_length=40, blank=True)
    coordinator = models.ForeignKey(
        "users.User",
        verbose_name="Coordinador de sede",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="coordinated_campuses",
    )
    is_main = models.BooleanField("Sede principal", default=False)

    class Meta:
        db_table = "institution_campus"
        verbose_name = "Sede"
        verbose_name_plural = "Sedes"
        unique_together = ("institution", "code")
        ordering = ["-is_main", "name"]

    def __str__(self):
        return self.name


class Shift(CatalogModel):
    """Jornada academica (manana, tarde, unica, nocturna)."""

    institution = models.ForeignKey(
        Institution, verbose_name="Institucion", on_delete=models.CASCADE, related_name="shifts"
    )
    start_time = models.TimeField("Hora de inicio", null=True, blank=True)
    end_time = models.TimeField("Hora de finalizacion", null=True, blank=True)

    class Meta:
        db_table = "institution_shift"
        verbose_name = "Jornada"
        verbose_name_plural = "Jornadas"
        unique_together = ("institution", "code")
        ordering = ["order", "name"]


class InstitutionalCalendar(BaseModel):
    """Fechas clave del calendario institucional."""

    TYPE_CHOICES = [
        ("ACADEMICO", "Academico"),
        ("FESTIVO", "Festivo"),
        ("INSTITUCIONAL", "Institucional"),
        ("EVALUACION", "Evaluacion"),
        ("RECESO", "Receso"),
    ]

    institution = models.ForeignKey(
        Institution, verbose_name="Institucion", on_delete=models.CASCADE, related_name="calendar_dates"
    )
    name = models.CharField("Nombre", max_length=160)
    event_type = models.CharField("Tipo", max_length=20, choices=TYPE_CHOICES, default="ACADEMICO")
    start_date = models.DateField("Fecha inicial")
    end_date = models.DateField("Fecha final", null=True, blank=True)
    description = models.TextField("Descripcion", blank=True)

    class Meta:
        db_table = "institution_calendar"
        verbose_name = "Fecha del calendario"
        verbose_name_plural = "Calendario institucional"
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.name} ({self.start_date})"
