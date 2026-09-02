"""
Configuracion transversal de la plataforma:
  * Encabezado de reportes
  * Decimas de notas (redondeo y aproximacion)
  * Parametros del sistema
"""
from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from django.db import models

from config.models_base import BaseModel


class ReportHeader(BaseModel):
    """Encabezado y pie de pagina aplicado a todos los reportes impresos."""

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="report_headers"
    )
    name = models.CharField("Nombre de la configuracion", max_length=120, default="Encabezado principal")
    line_1 = models.CharField("Linea 1", max_length=200, blank=True)
    line_2 = models.CharField("Linea 2", max_length=200, blank=True)
    line_3 = models.CharField("Linea 3", max_length=200, blank=True)
    line_4 = models.CharField("Linea 4", max_length=200, blank=True)
    show_logo = models.BooleanField("Mostrar logotipo", default=True)
    logo_position = models.CharField(
        "Posicion del logo",
        max_length=10,
        choices=[("left", "Izquierda"), ("center", "Centro"), ("right", "Derecha")],
        default="left",
    )
    show_seal = models.BooleanField("Mostrar sello", default=False)
    footer_text = models.CharField("Texto de pie de pagina", max_length=240, blank=True)
    show_page_numbers = models.BooleanField("Numerar paginas", default=True)
    show_print_date = models.BooleanField("Mostrar fecha de impresion", default=True)
    watermark = models.CharField("Marca de agua", max_length=80, blank=True)
    paper_size = models.CharField(
        "Tamano de papel", max_length=10, choices=[("A4", "A4"), ("LETTER", "Carta"), ("LEGAL", "Oficio")], default="LETTER"
    )
    orientation = models.CharField(
        "Orientacion", max_length=10, choices=[("P", "Vertical"), ("L", "Horizontal")], default="P"
    )
    margin_top = models.PositiveSmallIntegerField("Margen superior (mm)", default=15)
    margin_bottom = models.PositiveSmallIntegerField("Margen inferior (mm)", default=15)
    margin_left = models.PositiveSmallIntegerField("Margen izquierdo (mm)", default=12)
    margin_right = models.PositiveSmallIntegerField("Margen derecho (mm)", default=12)
    is_default = models.BooleanField("Encabezado por defecto", default=False)

    class Meta:
        db_table = "configuration_report_header"
        verbose_name = "Encabezado de reportes"
        verbose_name_plural = "Encabezados de reportes"
        ordering = ["-is_default", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            ReportHeader.objects.filter(institution=self.institution).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def active(cls, institution=None):
        queryset = cls.objects.filter(is_active=True)
        if institution:
            queryset = queryset.filter(institution=institution)
        return queryset.order_by("-is_default", "id").first()


class GradeDecimalConfig(BaseModel):
    """
    Decimas de notas: define como se aproximan las calificaciones
    al momento de consolidar periodos y boletines.
    """

    ROUNDING_CHOICES = [
        ("HALF_UP", "Aproximacion normal (0.5 sube)"),
        ("DOWN", "Truncar decimales"),
        ("UP_FROM", "Aproximar desde una decima especifica"),
        ("NONE", "Sin aproximacion"),
    ]

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="grade_decimals"
    )
    name = models.CharField("Nombre", max_length=120, default="Configuracion de decimas")
    decimals = models.PositiveSmallIntegerField("Numero de decimales", default=1)
    rounding_mode = models.CharField("Modo de aproximacion", max_length=12, choices=ROUNDING_CHOICES, default="HALF_UP")
    round_from = models.DecimalField(
        "Aproximar a partir de", max_digits=4, decimal_places=2, default=Decimal("0.50")
    )
    apply_to_period = models.BooleanField("Aplicar a notas de periodo", default=True)
    apply_to_area = models.BooleanField("Aplicar a promedio de area", default=True)
    apply_to_final = models.BooleanField("Aplicar a nota final", default=True)
    minimum_grade = models.DecimalField("Nota minima", max_digits=5, decimal_places=2, default=Decimal("1.00"))
    maximum_grade = models.DecimalField("Nota maxima", max_digits=5, decimal_places=2, default=Decimal("5.00"))
    passing_grade = models.DecimalField("Nota aprobatoria", max_digits=5, decimal_places=2, default=Decimal("3.00"))
    is_default = models.BooleanField("Configuracion por defecto", default=True)

    class Meta:
        db_table = "configuration_grade_decimal"
        verbose_name = "Configuracion de decimas"
        verbose_name_plural = "Decimas de notas"
        ordering = ["-is_default", "name"]

    def __str__(self):
        return f"{self.name} ({self.school_year})"

    def apply(self, value):
        """Aplica la politica de aproximacion configurada a un valor decimal."""
        if value is None:
            return None
        value = Decimal(str(value))
        quantum = Decimal(1).scaleb(-self.decimals)
        if self.rounding_mode == "NONE":
            return value
        if self.rounding_mode == "DOWN":
            return value.quantize(quantum, rounding=ROUND_DOWN)
        if self.rounding_mode == "UP_FROM":
            integer_part = value.quantize(Decimal("1"), rounding=ROUND_DOWN)
            fraction = value - integer_part
            if fraction >= self.round_from:
                return (integer_part + 1).quantize(quantum)
            return integer_part.quantize(quantum)
        return value.quantize(quantum, rounding=ROUND_HALF_UP)

    @classmethod
    def for_year(cls, school_year):
        return cls.objects.filter(school_year=school_year, is_active=True).order_by("-is_default", "id").first()


class SystemParameter(BaseModel):
    """Parametros clave/valor editables por el Super Administrador."""

    TYPE_CHOICES = [
        ("STRING", "Texto"),
        ("INT", "Numero entero"),
        ("DECIMAL", "Numero decimal"),
        ("BOOL", "Si / No"),
        ("JSON", "JSON"),
        ("DATE", "Fecha"),
    ]

    key = models.CharField("Clave", max_length=80, unique=True)
    label = models.CharField("Etiqueta", max_length=160)
    value = models.TextField("Valor", blank=True)
    value_type = models.CharField("Tipo", max_length=10, choices=TYPE_CHOICES, default="STRING")
    group = models.CharField("Grupo", max_length=60, default="General")
    help_text = models.CharField("Ayuda", max_length=240, blank=True)
    is_editable = models.BooleanField("Editable", default=True)

    class Meta:
        db_table = "configuration_parameter"
        verbose_name = "Parametro del sistema"
        verbose_name_plural = "Parametros del sistema"
        ordering = ["group", "label"]

    def __str__(self):
        return self.label

    @property
    def typed_value(self):
        import json

        raw = self.value
        try:
            if self.value_type == "INT":
                return int(raw)
            if self.value_type == "DECIMAL":
                return Decimal(raw)
            if self.value_type == "BOOL":
                return str(raw).lower() in ("1", "true", "si", "yes", "on")
            if self.value_type == "JSON":
                return json.loads(raw or "{}")
        except (ValueError, TypeError):
            return None
        return raw

    @classmethod
    def get(cls, key, default=None):
        parameter = cls.objects.filter(key=key, is_active=True).first()
        return parameter.typed_value if parameter else default
