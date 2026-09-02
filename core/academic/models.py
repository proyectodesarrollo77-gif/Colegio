"""
Directiva academica: estructura curricular y parametrizacion institucional.

  Ano lectivo -> Periodos -> Escala valorativa -> Dimensiones
  Niveles -> Grados -> Grupos
  Areas -> Asignaturas -> Procesos academicos -> Juicios valorativos
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from config.models_base import BaseModel, CatalogModel


class SchoolYear(BaseModel):
    STATUS_CHOICES = [
        ("PLANEACION", "En planeacion"),
        ("ACTIVO", "Activo"),
        ("CIERRE", "En cierre"),
        ("CERRADO", "Cerrado"),
    ]

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="school_years"
    )
    year = models.PositiveSmallIntegerField("Ano", db_index=True)
    name = models.CharField("Nombre", max_length=80)
    start_date = models.DateField("Fecha de inicio")
    end_date = models.DateField("Fecha de finalizacion")
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PLANEACION")
    is_current = models.BooleanField("Ano en curso", default=False)
    weeks = models.PositiveSmallIntegerField("Semanas academicas", default=40)
    enrollment_open = models.BooleanField("Matriculas abiertas", default=True)
    grades_locked = models.BooleanField("Notas bloqueadas", default=False)

    class Meta:
        db_table = "academic_school_year"
        verbose_name = "Ano lectivo"
        verbose_name_plural = "Anos lectivos"
        unique_together = ("institution", "year")
        ordering = ["-year"]

    def __str__(self):
        return self.name or str(self.year)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"Ano lectivo {self.year}"
        if self.is_current:
            SchoolYear.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        """Ano lectivo vigente de la institucion en la que se esta trabajando."""
        from core.institutions.context import get_active_institution

        queryset = cls.objects.filter(deleted_at__isnull=True)
        institution = get_active_institution()
        if institution is not None:
            queryset = queryset.filter(institution=institution)
        return queryset.filter(is_current=True).first() or queryset.order_by("-year").first()

    @property
    def progress(self):
        if not self.start_date or not self.end_date:
            return 0
        total = (self.end_date - self.start_date).days or 1
        elapsed = (timezone.localdate() - self.start_date).days
        return max(0, min(100, round(elapsed / total * 100)))


class AcademicPeriod(BaseModel):
    school_year = models.ForeignKey(
        SchoolYear, verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="periods"
    )
    number = models.PositiveSmallIntegerField("Numero de periodo")
    name = models.CharField("Nombre", max_length=80)
    short_name = models.CharField("Abreviatura", max_length=16, blank=True)
    start_date = models.DateField("Fecha de inicio")
    end_date = models.DateField("Fecha de finalizacion")
    weight = models.DecimalField(
        "Porcentaje (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("25.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    is_current = models.BooleanField("Periodo en curso", default=False)
    is_recovery = models.BooleanField("Periodo de recuperacion", default=False)
    grades_open = models.BooleanField("Digitacion de notas abierta", default=True)
    grades_open_from = models.DateTimeField("Apertura de digitacion", null=True, blank=True)
    grades_open_to = models.DateTimeField("Cierre de digitacion", null=True, blank=True)
    report_published = models.BooleanField("Boletin publicado", default=False)

    class Meta:
        db_table = "academic_period"
        verbose_name = "Periodo academico"
        verbose_name_plural = "Periodos academicos"
        unique_together = ("school_year", "number")
        ordering = ["school_year__year", "number"]

    def __str__(self):
        return f"{self.name} - {self.school_year}"

    def save(self, *args, **kwargs):
        if not self.short_name:
            self.short_name = f"P{self.number}"
        if self.is_current:
            AcademicPeriod.objects.filter(school_year=self.school_year).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @property
    def is_open_now(self):
        if not self.grades_open:
            return False
        now = timezone.now()
        if self.grades_open_from and now < self.grades_open_from:
            return False
        if self.grades_open_to and now > self.grades_open_to:
            return False
        return True


class GradingScale(BaseModel):
    """Escala valorativa institucional (cuantitativa o cualitativa)."""

    TYPE_CHOICES = [("NUMERICA", "Numerica"), ("CUALITATIVA", "Cualitativa"), ("MIXTA", "Mixta")]

    school_year = models.ForeignKey(
        SchoolYear, verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="grading_scales"
    )
    name = models.CharField("Nombre de la escala", max_length=120)
    scale_type = models.CharField("Tipo", max_length=12, choices=TYPE_CHOICES, default="NUMERICA")
    minimum = models.DecimalField("Valor minimo", max_digits=5, decimal_places=2, default=Decimal("1.00"))
    maximum = models.DecimalField("Valor maximo", max_digits=5, decimal_places=2, default=Decimal("5.00"))
    passing = models.DecimalField("Valor aprobatorio", max_digits=5, decimal_places=2, default=Decimal("3.00"))
    decimals = models.PositiveSmallIntegerField("Decimales", default=1)
    is_default = models.BooleanField("Escala por defecto", default=False)
    applies_to_preschool = models.BooleanField("Aplica a preescolar", default=False)

    class Meta:
        db_table = "academic_grading_scale"
        verbose_name = "Escala valorativa"
        verbose_name_plural = "Escalas valorativas"
        ordering = ["-is_default", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            GradingScale.objects.filter(school_year=self.school_year).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def level_for(self, value):
        if value is None:
            return None
        return self.levels.filter(minimum__lte=value, maximum__gte=value).order_by("order").first()

    @classmethod
    def default_for(cls, school_year):
        """Escala vigente del ano lectivo, preferiendo la activa."""
        if school_year is None:
            return None
        scales = school_year.grading_scales.filter(is_default=True)
        return scales.filter(is_active=True).first() or scales.first()


def resolve_performance(school_year, value):
    """
    Desempeno que corresponde a una nota segun la escala del ano lectivo.

    Es el unico punto donde se traduce un numero a Basico, Alto, Superior o
    Bajo, de modo que la planilla, el CRUD, la API, las importaciones y los
    comandos de consolidacion asignen siempre lo mismo.
    """
    scale = GradingScale.default_for(school_year)
    return scale.level_for(value) if scale else None


class GradingScaleLevel(BaseModel):
    """Desempeno de la escala: Superior, Alto, Basico, Bajo."""

    scale = models.ForeignKey(
        GradingScale, verbose_name="Escala", on_delete=models.CASCADE, related_name="levels"
    )
    code = models.CharField("Codigo", max_length=16)
    name = models.CharField("Desempeno", max_length=80)
    national_equivalent = models.CharField("Equivalencia nacional", max_length=80, blank=True)
    minimum = models.DecimalField("Desde", max_digits=5, decimal_places=2)
    maximum = models.DecimalField("Hasta", max_digits=5, decimal_places=2)
    color = models.CharField("Color", max_length=20, default="#10B981")
    is_passing = models.BooleanField("Aprueba", default=True)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "academic_grading_scale_level"
        verbose_name = "Nivel de desempeno"
        verbose_name_plural = "Niveles de desempeno"
        ordering = ["order", "-minimum"]

    def __str__(self):
        return f"{self.name} ({self.minimum} - {self.maximum})"


class ValuationDimension(CatalogModel):
    """Dimensiones valorativas: cognitiva, procedimental, actitudinal."""

    school_year = models.ForeignKey(
        SchoolYear, verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="dimensions"
    )
    weight = models.DecimalField("Porcentaje (%)", max_digits=5, decimal_places=2, default=Decimal("33.33"))
    applies_to_all = models.BooleanField("Aplica a todas las asignaturas", default=True)

    class Meta:
        db_table = "academic_valuation_dimension"
        verbose_name = "Dimension valorativa"
        verbose_name_plural = "Dimensiones valorativas"
        unique_together = ("school_year", "code")
        ordering = ["order", "name"]


class EducationLevel(CatalogModel):
    """Nivel educativo: Preescolar, Basica Primaria, Basica Secundaria, Media."""

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="levels"
    )
    is_preschool = models.BooleanField("Es preescolar", default=False)
    evaluation_type = models.CharField(
        "Tipo de evaluacion",
        max_length=14,
        choices=[("CUANTITATIVA", "Cuantitativa"), ("CUALITATIVA", "Cualitativa"), ("MIXTA", "Mixta")],
        default="CUANTITATIVA",
    )

    class Meta:
        db_table = "academic_education_level"
        verbose_name = "Nivel educativo"
        verbose_name_plural = "Niveles educativos"
        unique_together = ("institution", "code")
        ordering = ["order", "name"]


class Grade(CatalogModel):
    """Grado escolar (Transicion, 1o ... 11o)."""

    level = models.ForeignKey(
        EducationLevel, verbose_name="Nivel educativo", on_delete=models.CASCADE, related_name="grades"
    )
    numeric_value = models.SmallIntegerField("Valor numerico", default=0)
    next_grade = models.ForeignKey(
        "self", verbose_name="Grado siguiente", null=True, blank=True, on_delete=models.SET_NULL, related_name="previous_grades"
    )
    minimum_age = models.PositiveSmallIntegerField("Edad minima", default=0)
    maximum_age = models.PositiveSmallIntegerField("Edad maxima", default=0)
    is_graduation = models.BooleanField("Grado de graduacion", default=False)

    class Meta:
        db_table = "academic_grade"
        verbose_name = "Grado"
        verbose_name_plural = "Grados"
        ordering = ["order", "numeric_value"]


class Group(BaseModel):
    """Grupo o curso: 6-01, 6-02, etc."""

    school_year = models.ForeignKey(
        SchoolYear, verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="groups"
    )
    grade = models.ForeignKey(Grade, verbose_name="Grado", on_delete=models.CASCADE, related_name="groups")
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", null=True, blank=True, on_delete=models.SET_NULL, related_name="groups"
    )
    shift = models.ForeignKey(
        "institutions.Shift", verbose_name="Jornada", null=True, blank=True, on_delete=models.SET_NULL, related_name="groups"
    )
    code = models.CharField("Codigo", max_length=24)
    name = models.CharField("Nombre del grupo", max_length=80)
    capacity = models.PositiveSmallIntegerField("Cupo maximo", default=35)
    classroom = models.CharField("Aula", max_length=40, blank=True)
    director = models.ForeignKey(
        "teachers.Teacher",
        verbose_name="Director de grupo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="directed_groups",
    )
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "academic_group"
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"
        unique_together = ("school_year", "grade", "code")
        ordering = ["grade__order", "code"]

    def __str__(self):
        return self.name or f"{self.grade.name} {self.code}"

    @property
    def enrolled_count(self):
        return self.enrollments.filter(status="ACTIVA", deleted_at__isnull=True).count()

    @property
    def available_seats(self):
        return max(self.capacity - self.enrolled_count, 0)

    @property
    def occupancy(self):
        return round(self.enrolled_count / self.capacity * 100) if self.capacity else 0


class Area(CatalogModel):
    """Area obligatoria y fundamental."""

    school_year = models.ForeignKey(
        SchoolYear, verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="areas"
    )
    weight = models.DecimalField("Porcentaje del area (%)", max_digits=5, decimal_places=2, default=Decimal("100.00"))
    is_mandatory = models.BooleanField("Area obligatoria", default=True)
    color = models.CharField("Color", max_length=20, default="#6366F1")
    average_by_intensity = models.BooleanField("Promediar por intensidad horaria", default=True)

    class Meta:
        db_table = "academic_area"
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        unique_together = ("school_year", "code")
        ordering = ["order", "name"]


class Subject(CatalogModel):
    """Asignatura perteneciente a un area."""

    area = models.ForeignKey(Area, verbose_name="Area", on_delete=models.CASCADE, related_name="subjects")
    grades = models.ManyToManyField(Grade, verbose_name="Grados", blank=True, related_name="subjects")
    weekly_hours = models.PositiveSmallIntegerField("Intensidad horaria semanal", default=1)
    weight = models.DecimalField("Peso dentro del area (%)", max_digits=5, decimal_places=2, default=Decimal("100.00"))
    is_bilingual = models.BooleanField("Asignatura bilingue", default=False)
    affects_promotion = models.BooleanField("Afecta la promocion", default=True)
    allows_recovery = models.BooleanField("Permite recuperacion", default=True)
    evaluation_type = models.CharField(
        "Tipo de evaluacion",
        max_length=14,
        choices=[("CUANTITATIVA", "Cuantitativa"), ("CUALITATIVA", "Cualitativa")],
        default="CUANTITATIVA",
    )

    class Meta:
        db_table = "academic_subject"
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        ordering = ["area__order", "order", "name"]

    def __str__(self):
        return self.name


class AcademicProcess(BaseModel):
    """
    Proceso academico evaluado dentro de una asignatura y periodo
    (por ejemplo: Taller 1, Evaluacion final, Trabajo en clase).
    """

    school_year = models.ForeignKey(
        SchoolYear, verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="processes"
    )
    period = models.ForeignKey(
        AcademicPeriod, verbose_name="Periodo", null=True, blank=True, on_delete=models.CASCADE, related_name="processes"
    )
    subject = models.ForeignKey(
        Subject, verbose_name="Asignatura", null=True, blank=True, on_delete=models.CASCADE, related_name="processes"
    )
    dimension = models.ForeignKey(
        ValuationDimension,
        verbose_name="Dimension",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="processes",
    )
    code = models.CharField("Codigo", max_length=24)
    name = models.CharField("Nombre del proceso", max_length=160)
    description = models.TextField("Descripcion", blank=True)
    weight = models.DecimalField("Porcentaje (%)", max_digits=5, decimal_places=2, default=Decimal("100.00"))
    order = models.PositiveSmallIntegerField("Orden", default=0)
    applies_to_all_subjects = models.BooleanField("Aplica a todas las asignaturas", default=False)

    class Meta:
        db_table = "academic_process"
        verbose_name = "Proceso academico"
        verbose_name_plural = "Procesos academicos"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ValueJudgment(BaseModel):
    """
    Juicio valorativo / indicador de desempeno predefinido que el docente
    selecciona al calificar (fortalezas, debilidades, recomendaciones).
    """

    TYPE_CHOICES = [
        ("FORTALEZA", "Fortaleza"),
        ("DEBILIDAD", "Debilidad"),
        ("RECOMENDACION", "Recomendacion"),
        ("DESEMPENO", "Indicador de desempeno"),
    ]

    school_year = models.ForeignKey(
        SchoolYear, verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="judgments"
    )
    subject = models.ForeignKey(
        Subject, verbose_name="Asignatura", null=True, blank=True, on_delete=models.CASCADE, related_name="judgments"
    )
    grade = models.ForeignKey(
        Grade, verbose_name="Grado", null=True, blank=True, on_delete=models.CASCADE, related_name="judgments"
    )
    period = models.ForeignKey(
        AcademicPeriod, verbose_name="Periodo", null=True, blank=True, on_delete=models.CASCADE, related_name="judgments"
    )
    performance_level = models.ForeignKey(
        GradingScaleLevel,
        verbose_name="Desempeno asociado",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="judgments",
    )
    judgment_type = models.CharField("Tipo", max_length=16, choices=TYPE_CHOICES, default="DESEMPENO")
    code = models.CharField("Codigo", max_length=24, blank=True)
    text = models.TextField("Texto del juicio")
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "academic_value_judgment"
        verbose_name = "Juicio valorativo"
        verbose_name_plural = "Juicios valorativos"
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:80]


class CoexistenceItem(BaseModel):
    """Item de convivencia evaluado por el tutor o director de grupo."""

    TYPE_CHOICES = [
        ("COMPORTAMIENTO", "Comportamiento"),
        ("PUNTUALIDAD", "Puntualidad"),
        ("PRESENTACION", "Presentacion personal"),
        ("RESPONSABILIDAD", "Responsabilidad"),
        ("CONVIVENCIA", "Convivencia"),
    ]

    school_year = models.ForeignKey(
        SchoolYear, verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="coexistence_items"
    )
    code = models.CharField("Codigo", max_length=24)
    name = models.CharField("Nombre", max_length=160)
    item_type = models.CharField("Tipo", max_length=20, choices=TYPE_CHOICES, default="COMPORTAMIENTO")
    description = models.TextField("Descripcion", blank=True)
    weight = models.DecimalField("Porcentaje (%)", max_digits=5, decimal_places=2, default=Decimal("100.00"))
    affects_report = models.BooleanField("Aparece en el boletin", default=True)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "academic_coexistence_item"
        verbose_name = "Item de convivencia"
        verbose_name_plural = "Convivencia"
        unique_together = ("school_year", "code")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Purpose(BaseModel):
    """Propositos de preescolar por dimension del desarrollo."""

    school_year = models.ForeignKey(
        SchoolYear, verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="purposes"
    )
    grade = models.ForeignKey(
        Grade, verbose_name="Grado", null=True, blank=True, on_delete=models.CASCADE, related_name="purposes"
    )
    dimension = models.ForeignKey(
        ValuationDimension,
        verbose_name="Dimension del desarrollo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purposes",
    )
    period = models.ForeignKey(
        AcademicPeriod, verbose_name="Periodo", null=True, blank=True, on_delete=models.CASCADE, related_name="purposes"
    )
    code = models.CharField("Codigo", max_length=24, blank=True)
    text = models.TextField("Proposito")
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "academic_purpose"
        verbose_name = "Proposito"
        verbose_name_plural = "Propositos"
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:80]
