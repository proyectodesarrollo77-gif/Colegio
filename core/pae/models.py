"""
PL_SGE - Modulo de Gestion Integral del Programa de Alimentacion Escolar (PAE).

Principios de integracion con la plataforma existente:

  * NO se duplica informacion: institucion, sede, jornada, ano lectivo (vigencia),
    estudiante, matricula, grado, grupo, usuario y rol provienen de sus modulos.
  * Todos los modelos heredan de config.models_base.BaseModel, con lo que obtienen
    trazabilidad (created_by / updated_by), borrado logico, uuid publico y estado.
  * Las listas que la normativa puede modificar se administran mediante
    PaeCatalog (catalogo parametrizable multi-tipo) y no se codifican de forma
    rigida en el software.
  * Cada vigencia PAE registra la version normativa aplicable (PaeNormative),
    de modo que un cambio de resolucion no invalida los datos historicos.

Referencia normativa: la parametrizacion permite registrar las resoluciones
vigentes (por ejemplo Resolucion 0003 de 2026 y Resolucion 0155 de 2026 de la
UApA - Alimentos para Aprender). Los valores concretos exigidos por cada
resolucion se cargan como datos, no como codigo, y quedan marcados
"POR VALIDAR" hasta que la institucion confirme el texto oficial.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from config.models_base import BaseModel, CatalogModel

# ---------------------------------------------------------------------------
# Estados transversales
# ---------------------------------------------------------------------------
VALIDATION_STATUS = [
    ("VIGENTE", "Vigente"),
    ("POR_VALIDAR", "Por validar"),
    ("DEROGADO", "Derogado"),
]

COMPLIANCE_RESULT = [
    ("CUMPLE", "Cumple"),
    ("CUMPLE_PARCIAL", "Cumple parcialmente"),
    ("NO_CUMPLE", "No cumple"),
    ("SIN_EVALUAR", "Sin evaluar"),
]

PRIORITY_LEVELS = [
    ("BAJA", "Baja"),
    ("MEDIA", "Media"),
    ("ALTA", "Alta"),
    ("CRITICA", "Critica"),
]


# ===========================================================================
# 1. CONFIGURACION Y PARAMETRIZACION
# ===========================================================================
class PaeNormative(BaseModel):
    """
    Version normativa aplicable a una vigencia del programa.

    Permite actualizar la reglamentacion sin reescribir el software: cada
    vigencia PAE apunta a la norma que la rige y los datos historicos
    conservan la version con la que fueron producidos.
    """

    code = models.CharField("Codigo", max_length=40, unique=True)
    name = models.CharField("Norma", max_length=200)
    issuer = models.CharField("Entidad emisora", max_length=160, default="UApA - Alimentos para Aprender")
    number = models.CharField("Numero", max_length=40, blank=True)
    issued_on = models.DateField("Fecha de expedicion", null=True, blank=True)
    effective_from = models.DateField("Vigente desde", null=True, blank=True)
    effective_to = models.DateField("Vigente hasta", null=True, blank=True)
    status = models.CharField("Estado", max_length=12, choices=VALIDATION_STATUS, default="POR_VALIDAR")
    summary = models.TextField("Resumen", blank=True)
    url = models.URLField("Enlace oficial", blank=True)
    file = models.FileField("Documento", upload_to="pae/normativa/%Y/", null=True, blank=True)
    notes = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_normativa"
        verbose_name = "Norma del PAE"
        verbose_name_plural = "Normativa del PAE"
        ordering = ["-effective_from", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class PaeCatalog(CatalogModel):
    """
    Catalogo parametrizable multi-tipo.

    Reemplaza a una decena de tablas de listas fijas: criterios de priorizacion,
    tipos de novedad, tipos de visita, tipos de hallazgo, tipos de PQRS, tipos de
    documento, categorias de verificacion y estados configurables.
    """

    TYPE_CRITERION = "CRITERIO_PRIORIZACION"
    TYPE_INCIDENT = "TIPO_NOVEDAD"
    TYPE_VISIT = "TIPO_VISITA"
    TYPE_FINDING = "TIPO_HALLAZGO"
    TYPE_PQRS = "TIPO_PQRS"
    TYPE_DOCUMENT = "TIPO_DOCUMENTO"
    TYPE_CHECK_CATEGORY = "CATEGORIA_VERIFICACION"
    TYPE_POPULATION = "TIPO_POBLACION"
    TYPE_MEASURE_UNIT = "UNIDAD_MEDIDA"
    TYPE_FOOD_GROUP = "GRUPO_ALIMENTO"
    TYPE_MEETING = "TIPO_REUNION"
    TYPE_CAUSE = "CAUSA_INCUMPLIMIENTO"

    TYPE_CHOICES = [
        (TYPE_CRITERION, "Criterio de priorizacion"),
        (TYPE_INCIDENT, "Tipo de novedad"),
        (TYPE_VISIT, "Tipo de visita"),
        (TYPE_FINDING, "Tipo de hallazgo"),
        (TYPE_PQRS, "Tipo de PQRS"),
        (TYPE_DOCUMENT, "Tipo de documento"),
        (TYPE_CHECK_CATEGORY, "Categoria de verificacion"),
        (TYPE_POPULATION, "Tipo de poblacion"),
        (TYPE_MEASURE_UNIT, "Unidad de medida"),
        (TYPE_FOOD_GROUP, "Grupo de alimento"),
        (TYPE_MEETING, "Tipo de reunion"),
        (TYPE_CAUSE, "Causa de incumplimiento"),
    ]

    catalog_type = models.CharField("Tipo de catalogo", max_length=32, choices=TYPE_CHOICES, db_index=True)
    normative = models.ForeignKey(
        PaeNormative,
        verbose_name="Norma de referencia",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="catalog_entries",
    )
    weight = models.DecimalField("Peso / puntaje", max_digits=6, decimal_places=2, default=Decimal("0.00"))
    color = models.CharField("Color", max_length=20, default="#4F46E5")
    icon = models.CharField("Icono", max_length=40, blank=True)
    requires_evidence = models.BooleanField("Exige evidencia", default=False)
    requires_action = models.BooleanField("Genera accion correctiva", default=False)
    validation_status = models.CharField(
        "Estado normativo", max_length=12, choices=VALIDATION_STATUS, default="POR_VALIDAR"
    )
    metadata = models.JSONField("Datos adicionales", default=dict, blank=True)

    class Meta:
        db_table = "pae_catalogo"
        verbose_name = "Elemento de catalogo PAE"
        verbose_name_plural = "Catalogos del PAE"
        unique_together = ("catalog_type", "code")
        ordering = ["catalog_type", "order", "name"]
        indexes = [models.Index(fields=["catalog_type", "is_active"])]

    def __str__(self):
        return f"{self.name}"


class PaeModality(CatalogModel):
    """Modalidad de atencion: preparada en sitio, industrializada, racion para preparar en casa."""

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="pae_modalities"
    )
    requires_kitchen = models.BooleanField("Requiere cocina en sitio", default=True)
    requires_dining_room = models.BooleanField("Requiere comedor", default=True)
    requires_cold_chain = models.BooleanField("Requiere cadena de frio", default=False)
    normative = models.ForeignKey(
        PaeNormative, verbose_name="Norma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="modalities",
    )
    color = models.CharField("Color", max_length=20, default="#0EA5E9")

    class Meta:
        db_table = "pae_modalidad"
        verbose_name = "Modalidad de atencion"
        verbose_name_plural = "Modalidades de atencion"
        unique_together = ("institution", "code")
        ordering = ["order", "name"]


class PaeComplementType(CatalogModel):
    """
    Tipo de complemento alimentario (jornada manana, jornada tarde, almuerzo,
    jornada unica). Los aportes nutricionales son parametrizables por norma.
    """

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="pae_complements"
    )
    modality = models.ForeignKey(
        PaeModality, verbose_name="Modalidad", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="complement_types",
    )
    shift = models.ForeignKey(
        "institutions.Shift", verbose_name="Jornada", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_complement_types",
    )
    calorie_contribution = models.DecimalField(
        "Aporte calorico (kcal)", max_digits=8, decimal_places=2, default=Decimal("0.00"),
        help_text="Valor parametrizable segun la norma vigente. POR VALIDAR.",
    )
    energy_percentage = models.DecimalField(
        "Porcentaje del requerimiento diario", max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    service_start = models.TimeField("Hora de servicio (desde)", null=True, blank=True)
    service_end = models.TimeField("Hora de servicio (hasta)", null=True, blank=True)
    normative = models.ForeignKey(
        PaeNormative, verbose_name="Norma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="complement_types",
    )
    color = models.CharField("Color", max_length=20, default="#10B981")

    class Meta:
        db_table = "pae_tipo_complemento"
        verbose_name = "Tipo de complemento"
        verbose_name_plural = "Tipos de complemento"
        unique_together = ("institution", "code")
        ordering = ["order", "name"]


class PaeVigencia(BaseModel):
    """
    Vigencia del programa. Se apoya en el ano lectivo existente (academic.SchoolYear)
    y agrega la capa propia del PAE: norma aplicable, calendario de atencion y estado.
    """

    STATUS_CHOICES = [
        ("PLANEACION", "En planeacion"),
        ("ACTIVA", "Activa"),
        ("CIERRE", "En cierre"),
        ("CERRADA", "Cerrada"),
    ]

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="pae_vigencias"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.PROTECT, related_name="pae_vigencias"
    )
    normative = models.ForeignKey(
        PaeNormative, verbose_name="Norma aplicable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="vigencias",
    )
    name = models.CharField("Nombre de la vigencia", max_length=120)
    start_date = models.DateField("Fecha inicial")
    end_date = models.DateField("Fecha final")
    service_days = models.PositiveSmallIntegerField("Dias de atencion proyectados", default=180)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PLANEACION")
    is_current = models.BooleanField("Vigencia en curso", default=False)
    coverage_goal = models.DecimalField(
        "Meta de cobertura (%)", max_digits=5, decimal_places=2, default=Decimal("100.00")
    )
    compliance_goal = models.DecimalField(
        "Meta de cumplimiento (%)", max_digits=5, decimal_places=2, default=Decimal("95.00")
    )
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_vigencia"
        verbose_name = "Vigencia PAE"
        verbose_name_plural = "Vigencias PAE"
        unique_together = ("institution", "school_year")
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.name and self.school_year_id:
            self.name = f"PAE {self.school_year.year}"
        if self.is_current:
            PaeVigencia.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        return cls.objects.filter(is_current=True, deleted_at__isnull=True).first() or (
            cls.objects.filter(deleted_at__isnull=True).order_by("-start_date").first()
        )

    @property
    def progress(self):
        if not self.start_date or not self.end_date:
            return 0
        total = (self.end_date - self.start_date).days or 1
        elapsed = (timezone.localdate() - self.start_date).days
        return max(0, min(100, round(elapsed / total * 100)))


# ===========================================================================
# 2. DIAGNOSTICO DE SEDE
# ===========================================================================
class PaeSiteDiagnosis(BaseModel):
    """Diagnostico de infraestructura y condiciones de la sede por vigencia."""

    CONDITION_CHOICES = [
        ("OPTIMA", "Optima"),
        ("ACEPTABLE", "Aceptable"),
        ("DEFICIENTE", "Deficiente"),
        ("NO_EXISTE", "No existe"),
        ("NO_APLICA", "No aplica"),
    ]
    ZONE_CHOICES = [("URBANA", "Urbana"), ("RURAL", "Rural"), ("RURAL_DISPERSA", "Rural dispersa")]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="diagnoses"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", on_delete=models.CASCADE, related_name="pae_diagnoses"
    )
    diagnosis_date = models.DateField("Fecha del diagnostico", default=timezone.localdate)
    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_diagnoses",
    )

    zone = models.CharField("Zona", max_length=16, choices=ZONE_CHOICES, default="URBANA")
    infrastructure = models.CharField("Infraestructura general", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    kitchen = models.CharField("Cocina", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    dining_room = models.CharField("Comedor", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    storage = models.CharField("Bodega", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    refrigeration = models.CharField("Refrigeracion", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    water = models.CharField("Suministro de agua", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    energy = models.CharField("Energia electrica", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    gas = models.CharField("Gas / combustible", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    equipment = models.CharField("Equipos y menaje", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    sanitary = models.CharField("Condiciones sanitarias", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")
    accessibility = models.CharField("Accesibilidad", max_length=12, choices=CONDITION_CHOICES, default="ACEPTABLE")

    has_potable_water = models.BooleanField("Agua potable disponible", default=True)
    has_handwashing = models.BooleanField("Lavamanos disponible", default=True)
    has_waste_management = models.BooleanField("Manejo de residuos", default=True)
    has_pest_control = models.BooleanField("Control de plagas", default=False)
    has_sanitary_concept = models.BooleanField("Concepto sanitario favorable", default=False)

    dining_capacity = models.PositiveIntegerField("Capacidad del comedor (puestos)", default=0)
    kitchen_area_m2 = models.DecimalField("Area de cocina (m2)", max_digits=8, decimal_places=2, default=Decimal("0.00"))
    storage_area_m2 = models.DecimalField("Area de bodega (m2)", max_digits=8, decimal_places=2, default=Decimal("0.00"))
    max_rations = models.PositiveIntegerField("Capacidad maxima de raciones", default=0)
    food_handlers = models.PositiveSmallIntegerField("Manipuladores de alimentos", default=0)

    territorial_conditions = models.TextField("Condiciones territoriales", blank=True)
    observations = models.TextField("Observaciones", blank=True)
    result = models.CharField("Resultado", max_length=16, choices=COMPLIANCE_RESULT, default="SIN_EVALUAR")
    score = models.DecimalField("Puntaje (%)", max_digits=5, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "pae_diagnostico"
        verbose_name = "Diagnostico de sede"
        verbose_name_plural = "Diagnosticos de sede"
        unique_together = ("vigencia", "campus")
        ordering = ["-diagnosis_date"]

    def __str__(self):
        return f"Diagnostico {self.campus} - {self.vigencia}"

    CONDITION_SCORES = {"OPTIMA": 100, "ACEPTABLE": 70, "DEFICIENTE": 30, "NO_EXISTE": 0, "NO_APLICA": None}
    CONDITION_FIELDS = (
        "infrastructure", "kitchen", "dining_room", "storage", "refrigeration",
        "water", "energy", "gas", "equipment", "sanitary", "accessibility",
    )

    def compute_score(self):
        """Puntaje ponderado de las condiciones evaluadas, ignorando 'no aplica'."""
        values = [
            self.CONDITION_SCORES.get(getattr(self, name))
            for name in self.CONDITION_FIELDS
        ]
        values = [value for value in values if value is not None]
        if not values:
            self.score = Decimal("0.00")
            self.result = "SIN_EVALUAR"
            return self.score
        average = sum(values) / len(values)
        self.score = Decimal(str(round(average, 2)))
        if average >= 85:
            self.result = "CUMPLE"
        elif average >= 60:
            self.result = "CUMPLE_PARCIAL"
        else:
            self.result = "NO_CUMPLE"
        return self.score

    def save(self, *args, **kwargs):
        self.compute_score()
        super().save(*args, **kwargs)


# ===========================================================================
# 3. PRIORIZACION
# ===========================================================================
class PaePrioritization(BaseModel):
    """Focalizacion de la poblacion a atender por sede, grado y grupo."""

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("EN_REVISION", "En revision"),
        ("APROBADA", "Aprobada"),
        ("RECHAZADA", "Rechazada"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="prioritizations"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", on_delete=models.CASCADE, related_name="pae_prioritizations"
    )
    grade = models.ForeignKey(
        "academic.Grade", verbose_name="Grado", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_prioritizations",
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_prioritizations",
    )
    shift = models.ForeignKey(
        "institutions.Shift", verbose_name="Jornada", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_prioritizations",
    )
    population_type = models.ForeignKey(
        PaeCatalog, verbose_name="Tipo de poblacion", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="prioritizations_population",
        limit_choices_to={"catalog_type": PaeCatalog.TYPE_POPULATION},
    )
    criteria = models.ManyToManyField(
        PaeCatalog, verbose_name="Criterios aplicados", blank=True, related_name="prioritizations_criteria",
        limit_choices_to={"catalog_type": PaeCatalog.TYPE_CRITERION},
    )

    enrolled_students = models.PositiveIntegerField("Estudiantes matriculados", default=0)
    prioritized_students = models.PositiveIntegerField("Estudiantes priorizados", default=0)
    score = models.DecimalField("Puntaje de priorizacion", max_digits=8, decimal_places=2, default=Decimal("0.00"))
    justification = models.TextField("Justificacion", blank=True)
    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_prioritizations",
    )
    registered_on = models.DateField("Fecha de registro", default=timezone.localdate)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="BORRADOR")
    approved_by = models.ForeignKey(
        "users.User", verbose_name="Aprobado por", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_prioritizations_approved",
    )
    approved_at = models.DateTimeField("Aprobada el", null=True, blank=True)

    class Meta:
        db_table = "pae_priorizacion"
        verbose_name = "Priorizacion"
        verbose_name_plural = "Priorizaciones"
        ordering = ["campus__name", "grade__order"]
        indexes = [models.Index(fields=["vigencia", "campus"])]

    def __str__(self):
        return f"{self.campus} / {self.grade or 'Todos los grados'} ({self.vigencia})"

    @property
    def coverage(self):
        if not self.enrolled_students:
            return 0
        return round(self.prioritized_students / self.enrolled_students * 100, 2)


# ===========================================================================
# 4. BENEFICIARIOS
# ===========================================================================
class PaeBeneficiary(BaseModel):
    """
    Beneficiario del programa.

    NO duplica al estudiante: lo referencia junto con su matricula vigente y
    agrega la informacion propia del PAE (modalidad, complemento, vigencia).
    """

    STATUS_CHOICES = [
        ("ACTIVO", "Activo"),
        ("SUSPENDIDO", "Suspendido"),
        ("RETIRADO", "Retirado"),
        ("TRASLADADO", "Trasladado"),
        ("FINALIZADO", "Finalizado"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="beneficiaries"
    )
    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", on_delete=models.CASCADE, related_name="pae_beneficiaries"
    )
    enrollment = models.ForeignKey(
        "students.Enrollment", verbose_name="Matricula", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_beneficiaries",
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_beneficiaries",
    )
    grade = models.ForeignKey(
        "academic.Grade", verbose_name="Grado", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_beneficiaries",
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_beneficiaries",
    )
    shift = models.ForeignKey(
        "institutions.Shift", verbose_name="Jornada", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_beneficiaries",
    )
    modality = models.ForeignKey(
        PaeModality, verbose_name="Modalidad", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="beneficiaries",
    )
    complement_type = models.ForeignKey(
        PaeComplementType, verbose_name="Tipo de complemento", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="beneficiaries",
    )
    prioritization = models.ForeignKey(
        PaePrioritization, verbose_name="Priorizacion", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="beneficiaries",
    )

    start_date = models.DateField("Fecha de inicio", default=timezone.localdate)
    end_date = models.DateField("Fecha final", null=True, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="ACTIVO", db_index=True)
    has_special_diet = models.BooleanField("Requiere dieta especial", default=False)
    special_diet_detail = models.CharField("Detalle de la dieta", max_length=240, blank=True)
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_beneficiario"
        verbose_name = "Beneficiario PAE"
        verbose_name_plural = "Beneficiarios PAE"
        unique_together = ("vigencia", "student")
        ordering = ["student__last_name", "student__first_name"]
        indexes = [
            models.Index(fields=["vigencia", "status"]),
            models.Index(fields=["campus", "status"]),
        ]

    def __str__(self):
        return f"{self.student} ({self.vigencia})"

    def save(self, *args, **kwargs):
        # Deriva sede, grado, grupo y jornada de la matricula si no vienen informados.
        if self.enrollment_id and not self.group_id:
            self.group = self.enrollment.group
        if self.group_id:
            self.grade = self.grade or self.group.grade
            self.campus = self.campus or self.group.campus
            self.shift = self.shift or self.group.shift
        super().save(*args, **kwargs)


class PaeBeneficiaryHistory(BaseModel):
    """Historial de cambios de estado del beneficiario (trazabilidad obligatoria)."""

    beneficiary = models.ForeignKey(
        PaeBeneficiary, verbose_name="Beneficiario", on_delete=models.CASCADE, related_name="history"
    )
    previous_status = models.CharField("Estado anterior", max_length=12, blank=True)
    new_status = models.CharField("Estado nuevo", max_length=12)
    previous_group = models.CharField("Grupo anterior", max_length=80, blank=True)
    new_group = models.CharField("Grupo nuevo", max_length=80, blank=True)
    reason = models.CharField("Motivo del cambio", max_length=240, blank=True)
    changed_at = models.DateTimeField("Fecha del cambio", default=timezone.now)
    changed_by = models.ForeignKey(
        "users.User", verbose_name="Realizado por", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_beneficiary_changes",
    )

    class Meta:
        db_table = "pae_beneficiario_historial"
        verbose_name = "Historial de beneficiario"
        verbose_name_plural = "Historial de beneficiarios"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.beneficiary} : {self.previous_status} -> {self.new_status}"


# ===========================================================================
# 5. OPERADORES Y CONTRATOS
# ===========================================================================
class PaeOperator(BaseModel):
    """Operador responsable de la prestacion del servicio de alimentacion."""

    STATUS_CHOICES = [
        ("ACTIVO", "Activo"),
        ("SUSPENDIDO", "Suspendido"),
        ("INACTIVO", "Inactivo"),
    ]

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="pae_operators"
    )
    code = models.CharField("Codigo", max_length=32)
    business_name = models.CharField("Razon social", max_length=200)
    nit = models.CharField("NIT", max_length=32, unique=True)
    legal_representative = models.CharField("Representante legal", max_length=180, blank=True)
    contact_name = models.CharField("Persona de contacto", max_length=180, blank=True)
    phone = models.CharField("Telefono", max_length=32, blank=True)
    mobile = models.CharField("Celular", max_length=32, blank=True)
    email = models.EmailField("Correo electronico", blank=True)
    address = models.CharField("Direccion", max_length=200, blank=True)
    city = models.CharField("Ciudad", max_length=120, blank=True)
    sanitary_registration = models.CharField("Registro sanitario", max_length=80, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="ACTIVO")
    user = models.ForeignKey(
        "users.User", verbose_name="Usuario de acceso", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_operator_profile",
    )
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_operador"
        verbose_name = "Operador"
        verbose_name_plural = "Operadores"
        unique_together = ("institution", "code")
        ordering = ["business_name"]

    def __str__(self):
        return self.business_name


class PaeContract(BaseModel):
    """Contrato suscrito con el operador."""

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("VIGENTE", "Vigente"),
        ("SUSPENDIDO", "Suspendido"),
        ("VENCIDO", "Vencido"),
        ("LIQUIDADO", "Liquidado"),
        ("TERMINADO", "Terminado"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="contracts"
    )
    operator = models.ForeignKey(
        PaeOperator, verbose_name="Operador", on_delete=models.PROTECT, related_name="contracts"
    )
    number = models.CharField("Numero de contrato", max_length=60)
    subject = models.TextField("Objeto del contrato")
    value = models.DecimalField("Valor", max_digits=16, decimal_places=2, default=Decimal("0.00"))
    ration_value = models.DecimalField("Valor unitario de la racion", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    start_date = models.DateField("Fecha inicial")
    end_date = models.DateField("Fecha final")
    total_rations = models.PositiveIntegerField("Raciones contratadas", default=0)
    campuses = models.ManyToManyField(
        "institutions.Campus", verbose_name="Sedes cubiertas", blank=True, related_name="pae_contracts"
    )
    modalities = models.ManyToManyField(
        PaeModality, verbose_name="Modalidades", blank=True, related_name="contracts"
    )
    supervisor = models.ForeignKey(
        "users.User", verbose_name="Supervisor del contrato", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_supervised_contracts",
    )
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="BORRADOR")
    alert_days = models.PositiveSmallIntegerField("Alertar dias antes del vencimiento", default=30)
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_contrato"
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        unique_together = ("vigencia", "number")
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.number} - {self.operator}"

    @property
    def days_to_expire(self):
        if not self.end_date:
            return None
        return (self.end_date - timezone.localdate()).days

    @property
    def is_expiring(self):
        days = self.days_to_expire
        return days is not None and 0 <= days <= self.alert_days

    @property
    def is_expired(self):
        days = self.days_to_expire
        return days is not None and days < 0

    @property
    def executed_rations(self):
        return (
            self.deliveries.filter(deleted_at__isnull=True).aggregate(total=models.Sum("delivered_rations"))["total"]
            or 0
        )

    @property
    def execution_percentage(self):
        if not self.total_rations:
            return 0
        return round(self.executed_rations / self.total_rations * 100, 2)


# ===========================================================================
# 6. PLANEACION
# ===========================================================================
class PaePlan(BaseModel):
    """Plan operativo del PAE por sede y vigencia."""

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("EN_REVISION", "En revision"),
        ("APROBADO", "Aprobado"),
        ("EN_EJECUCION", "En ejecucion"),
        ("CERRADO", "Cerrado"),
    ]

    # Transiciones permitidas y accion requerida para ejecutarlas.
    TRANSITIONS = {
        "BORRADOR": [("EN_REVISION", "edit")],
        "EN_REVISION": [("APROBADO", "approve"), ("BORRADOR", "edit")],
        "APROBADO": [("EN_EJECUCION", "approve"), ("EN_REVISION", "approve")],
        "EN_EJECUCION": [("CERRADO", "approve")],
        "CERRADO": [],
    }

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="plans"
    )
    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="pae_plans"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", on_delete=models.CASCADE, related_name="pae_plans"
    )
    code = models.CharField("Codigo del plan", max_length=40, blank=True, db_index=True)
    name = models.CharField("Nombre del plan", max_length=180)
    start_date = models.DateField("Fecha inicial")
    end_date = models.DateField("Fecha final")
    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_plans",
    )
    modality = models.ForeignKey(
        PaeModality, verbose_name="Modalidad", null=True, blank=True, on_delete=models.SET_NULL, related_name="plans"
    )
    complement_type = models.ForeignKey(
        PaeComplementType, verbose_name="Tipo de complemento", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="plans",
    )
    operator = models.ForeignKey(
        PaeOperator, verbose_name="Operador", null=True, blank=True, on_delete=models.SET_NULL, related_name="plans"
    )
    contract = models.ForeignKey(
        PaeContract, verbose_name="Contrato", null=True, blank=True, on_delete=models.SET_NULL, related_name="plans"
    )
    menu_cycle = models.ForeignKey(
        "pae.PaeMenuCycle", verbose_name="Ciclo de menu", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="plans",
    )

    beneficiaries_count = models.PositiveIntegerField("Beneficiarios", default=0)
    service_days = models.PositiveSmallIntegerField("Dias de atencion", default=0)
    projected_rations = models.PositiveIntegerField("Raciones proyectadas", default=0)

    status = models.CharField("Estado", max_length=14, choices=STATUS_CHOICES, default="BORRADOR", db_index=True)
    approved_by = models.ForeignKey(
        "users.User", verbose_name="Aprobado por", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_plans_approved",
    )
    approved_at = models.DateTimeField("Aprobado el", null=True, blank=True)
    closed_at = models.DateTimeField("Cerrado el", null=True, blank=True)
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_plan"
        verbose_name = "Plan PAE"
        verbose_name_plural = "Planes PAE"
        unique_together = ("vigencia", "campus", "name")
        ordering = ["-start_date", "campus__name"]

    def __str__(self):
        return f"{self.name} - {self.campus}"

    def save(self, *args, **kwargs):
        if not self.code:
            year = self.vigencia.school_year.year if self.vigencia_id else timezone.localdate().year
            count = PaePlan.objects.filter(vigencia=self.vigencia).count() + 1
            self.code = f"PAE-{year}-{count:03d}"
        if not self.projected_rations and self.beneficiaries_count and self.service_days:
            self.projected_rations = self.beneficiaries_count * self.service_days
        super().save(*args, **kwargs)

    def allowed_transitions(self):
        return self.TRANSITIONS.get(self.status, [])

    @property
    def is_editable(self):
        return self.status in ("BORRADOR", "EN_REVISION")


class PaePlanStateHistory(BaseModel):
    """Historial de transiciones de estado del plan."""

    plan = models.ForeignKey(PaePlan, verbose_name="Plan", on_delete=models.CASCADE, related_name="state_history")
    previous_status = models.CharField("Estado anterior", max_length=14, blank=True)
    new_status = models.CharField("Estado nuevo", max_length=14)
    reason = models.CharField("Motivo", max_length=240, blank=True)
    changed_at = models.DateTimeField("Fecha", default=timezone.now)
    changed_by = models.ForeignKey(
        "users.User", verbose_name="Realizado por", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_plan_changes",
    )

    class Meta:
        db_table = "pae_plan_historial"
        verbose_name = "Historial del plan"
        verbose_name_plural = "Historial de planes"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.plan}: {self.previous_status} -> {self.new_status}"


# ===========================================================================
# 7. CICLOS DE MENU
# ===========================================================================
class PaeMenuCycle(BaseModel):
    """Ciclo de menu con versionamiento."""

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("EN_REVISION", "En revision"),
        ("APROBADO", "Aprobado"),
        ("VIGENTE", "Vigente"),
        ("ARCHIVADO", "Archivado"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="menu_cycles"
    )
    modality = models.ForeignKey(
        PaeModality, verbose_name="Modalidad", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="menu_cycles",
    )
    complement_type = models.ForeignKey(
        PaeComplementType, verbose_name="Tipo de complemento", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="menu_cycles",
    )
    code = models.CharField("Codigo", max_length=32)
    name = models.CharField("Nombre del ciclo", max_length=180)
    version = models.PositiveSmallIntegerField("Version", default=1)
    days_count = models.PositiveSmallIntegerField("Dias del ciclo", default=5)
    start_date = models.DateField("Vigente desde", null=True, blank=True)
    end_date = models.DateField("Vigente hasta", null=True, blank=True)
    nutritionist = models.CharField("Nutricionista responsable", max_length=180, blank=True)
    professional_card = models.CharField("Tarjeta profesional", max_length=60, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="BORRADOR")
    parent_version = models.ForeignKey(
        "self", verbose_name="Version anterior", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="new_versions",
    )
    normative = models.ForeignKey(
        PaeNormative, verbose_name="Norma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="menu_cycles",
    )
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_menu_ciclo"
        verbose_name = "Ciclo de menu"
        verbose_name_plural = "Ciclos de menu"
        unique_together = ("vigencia", "code", "version")
        ordering = ["-version", "name"]

    def __str__(self):
        return f"{self.name} v{self.version}"

    def create_new_version(self, user=None):
        """Clona el ciclo completo en una version superior conservando el original."""
        from django.db import transaction

        with transaction.atomic():
            days = list(self.days.filter(deleted_at__isnull=True).prefetch_related("preparations__ingredients"))
            clone = PaeMenuCycle.objects.create(
                vigencia=self.vigencia,
                modality=self.modality,
                complement_type=self.complement_type,
                code=self.code,
                name=self.name,
                version=self.version + 1,
                days_count=self.days_count,
                start_date=self.start_date,
                end_date=self.end_date,
                nutritionist=self.nutritionist,
                professional_card=self.professional_card,
                status="BORRADOR",
                parent_version=self,
                normative=self.normative,
                observations=self.observations,
                created_by=user,
            )
            for day in days:
                new_day = PaeMenuDay.objects.create(
                    cycle=clone, day_number=day.day_number, weekday=day.weekday,
                    name=day.name, notes=day.notes, created_by=user,
                )
                for preparation in day.preparations.filter(deleted_at__isnull=True):
                    new_preparation = PaeMenuPreparation.objects.create(
                        day=new_day, name=preparation.name, component=preparation.component,
                        portion=preparation.portion, calories=preparation.calories,
                        protein=preparation.protein, notes=preparation.notes, order=preparation.order,
                        created_by=user,
                    )
                    for ingredient in preparation.ingredients.filter(deleted_at__isnull=True):
                        PaeMenuIngredient.objects.create(
                            preparation=new_preparation, name=ingredient.name,
                            food_group=ingredient.food_group, quantity=ingredient.quantity,
                            unit=ingredient.unit, notes=ingredient.notes, created_by=user,
                        )
            self.status = "ARCHIVADO"
            self.save(update_fields=["status"])
        return clone


class PaeMenuDay(BaseModel):
    """Dia dentro del ciclo de menu."""

    WEEKDAYS = [
        (1, "Lunes"), (2, "Martes"), (3, "Miercoles"),
        (4, "Jueves"), (5, "Viernes"), (6, "Sabado"), (7, "Domingo"),
    ]

    cycle = models.ForeignKey(PaeMenuCycle, verbose_name="Ciclo", on_delete=models.CASCADE, related_name="days")
    day_number = models.PositiveSmallIntegerField("Dia del ciclo", default=1)
    weekday = models.PositiveSmallIntegerField("Dia de la semana", choices=WEEKDAYS, null=True, blank=True)
    name = models.CharField("Nombre del menu", max_length=180, blank=True)
    notes = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_menu_dia"
        verbose_name = "Dia del ciclo"
        verbose_name_plural = "Dias del ciclo"
        unique_together = ("cycle", "day_number")
        ordering = ["day_number"]

    def __str__(self):
        return f"{self.cycle} - Dia {self.day_number}"

    @property
    def total_calories(self):
        return self.preparations.filter(deleted_at__isnull=True).aggregate(
            total=models.Sum("calories")
        )["total"] or Decimal("0.00")


class PaeMenuPreparation(BaseModel):
    """Preparacion servida en un dia del ciclo."""

    COMPONENT_CHOICES = [
        ("BEBIDA", "Bebida"),
        ("CEREAL", "Cereal / derivado"),
        ("PROTEICO", "Alimento proteico"),
        ("FRUTA", "Fruta"),
        ("VERDURA", "Verdura / hortaliza"),
        ("LACTEO", "Lacteo"),
        ("ACOMPANAMIENTO", "Acompanamiento"),
        ("POSTRE", "Postre"),
        ("OTRO", "Otro"),
    ]

    day = models.ForeignKey(PaeMenuDay, verbose_name="Dia", on_delete=models.CASCADE, related_name="preparations")
    name = models.CharField("Preparacion", max_length=180)
    component = models.CharField("Componente", max_length=16, choices=COMPONENT_CHOICES, default="OTRO")
    portion = models.CharField("Porcion servida", max_length=80, blank=True)
    calories = models.DecimalField("Calorias (kcal)", max_digits=8, decimal_places=2, default=Decimal("0.00"))
    protein = models.DecimalField("Proteina (g)", max_digits=8, decimal_places=2, default=Decimal("0.00"))
    notes = models.CharField("Observaciones", max_length=240, blank=True)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "pae_menu_preparacion"
        verbose_name = "Preparacion"
        verbose_name_plural = "Preparaciones"
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class PaeMenuIngredient(BaseModel):
    """Ingrediente y cantidad de una preparacion."""

    preparation = models.ForeignKey(
        PaeMenuPreparation, verbose_name="Preparacion", on_delete=models.CASCADE, related_name="ingredients"
    )
    name = models.CharField("Ingrediente", max_length=180)
    food_group = models.ForeignKey(
        PaeCatalog, verbose_name="Grupo de alimento", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="menu_ingredients",
        limit_choices_to={"catalog_type": PaeCatalog.TYPE_FOOD_GROUP},
    )
    quantity = models.DecimalField("Cantidad", max_digits=10, decimal_places=3, default=Decimal("0.000"))
    unit = models.CharField("Unidad", max_length=20, default="g")
    notes = models.CharField("Observaciones", max_length=240, blank=True)

    class Meta:
        db_table = "pae_menu_ingrediente"
        verbose_name = "Ingrediente"
        verbose_name_plural = "Ingredientes"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"


# ===========================================================================
# 8. PROGRAMACION Y ENTREGAS
# ===========================================================================
class PaeSchedule(BaseModel):
    """Programacion diaria de entrega por sede y jornada."""

    STATUS_CHOICES = [
        ("PROGRAMADA", "Programada"),
        ("CONFIRMADA", "Confirmada"),
        ("EJECUTADA", "Ejecutada"),
        ("CANCELADA", "Cancelada"),
    ]

    plan = models.ForeignKey(PaePlan, verbose_name="Plan", on_delete=models.CASCADE, related_name="schedules")
    service_date = models.DateField("Fecha de servicio", db_index=True)
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", on_delete=models.CASCADE, related_name="pae_schedules"
    )
    shift = models.ForeignKey(
        "institutions.Shift", verbose_name="Jornada", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_schedules",
    )
    operator = models.ForeignKey(
        PaeOperator, verbose_name="Operador", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="schedules",
    )
    complement_type = models.ForeignKey(
        PaeComplementType, verbose_name="Tipo de complemento", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="schedules",
    )
    menu_day = models.ForeignKey(
        PaeMenuDay, verbose_name="Menu programado", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="schedules",
    )
    beneficiaries_count = models.PositiveIntegerField("Beneficiarios programados", default=0)
    scheduled_rations = models.PositiveIntegerField("Raciones programadas", default=0)
    service_time = models.TimeField("Horario de servicio", null=True, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PROGRAMADA")
    observations = models.CharField("Observaciones", max_length=240, blank=True)

    class Meta:
        db_table = "pae_programacion"
        verbose_name = "Programacion"
        verbose_name_plural = "Programaciones"
        unique_together = ("plan", "service_date", "campus", "shift", "complement_type")
        ordering = ["-service_date", "campus__name"]
        indexes = [models.Index(fields=["service_date", "campus"])]

    def __str__(self):
        return f"{self.campus} - {self.service_date}"


class PaeDelivery(BaseModel):
    """
    Entrega diaria efectiva.

    Calcula de forma automatica faltantes, no entregadas y porcentaje de
    cumplimiento; exige justificacion cuando hay incumplimiento.
    """

    STATUS_CHOICES = [
        ("REGISTRADA", "Registrada"),
        ("VERIFICADA", "Verificada"),
        ("CON_NOVEDAD", "Con novedad"),
        ("ANULADA", "Anulada"),
    ]

    schedule = models.ForeignKey(
        PaeSchedule, verbose_name="Programacion", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    plan = models.ForeignKey(PaePlan, verbose_name="Plan", on_delete=models.CASCADE, related_name="deliveries")
    contract = models.ForeignKey(
        PaeContract, verbose_name="Contrato", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    service_date = models.DateField("Fecha", default=timezone.localdate, db_index=True)
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", on_delete=models.CASCADE, related_name="pae_deliveries"
    )
    shift = models.ForeignKey(
        "institutions.Shift", verbose_name="Jornada", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_deliveries",
    )
    operator = models.ForeignKey(
        PaeOperator, verbose_name="Operador", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    complement_type = models.ForeignKey(
        PaeComplementType, verbose_name="Tipo de complemento", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="deliveries",
    )

    scheduled_beneficiaries = models.PositiveIntegerField("Beneficiarios programados", default=0)
    scheduled_rations = models.PositiveIntegerField("Raciones programadas", default=0)
    received_rations = models.PositiveIntegerField("Raciones recibidas", default=0)
    delivered_rations = models.PositiveIntegerField("Raciones entregadas", default=0)
    missing_rations = models.IntegerField("Raciones faltantes", default=0, editable=False)
    undelivered_rations = models.IntegerField("Raciones no entregadas", default=0, editable=False)
    compliance = models.DecimalField(
        "Cumplimiento (%)", max_digits=6, decimal_places=2, default=Decimal("0.00"), editable=False
    )

    arrival_time = models.TimeField("Hora de llegada", null=True, blank=True)
    delivery_time = models.TimeField("Hora de entrega", null=True, blank=True)
    scheduled_menu = models.ForeignKey(
        PaeMenuDay, verbose_name="Menu programado", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="scheduled_deliveries",
    )
    menu_matches = models.BooleanField("El menu recibido corresponde al programado", default=True)
    received_menu_detail = models.CharField("Menu recibido", max_length=240, blank=True)

    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable del registro", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_deliveries",
    )
    noncompliance_cause = models.ForeignKey(
        PaeCatalog, verbose_name="Causa del incumplimiento", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="deliveries",
        limit_choices_to={"catalog_type": PaeCatalog.TYPE_CAUSE},
    )
    justification = models.TextField("Justificacion del incumplimiento", blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="REGISTRADA")
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_entrega"
        verbose_name = "Entrega diaria"
        verbose_name_plural = "Entregas diarias"
        unique_together = ("plan", "service_date", "campus", "shift", "complement_type")
        ordering = ["-service_date", "campus__name"]
        indexes = [
            models.Index(fields=["service_date", "campus"]),
            models.Index(fields=["plan", "status"]),
        ]

    def __str__(self):
        return f"Entrega {self.campus} - {self.service_date}"

    def compute_totals(self):
        """Regla de negocio: faltantes, no entregadas y cumplimiento."""
        self.missing_rations = int(self.scheduled_rations) - int(self.received_rations)
        self.undelivered_rations = int(self.received_rations) - int(self.delivered_rations)
        if self.scheduled_rations:
            self.compliance = Decimal(
                str(round(self.delivered_rations / self.scheduled_rations * 100, 2))
            )
        else:
            self.compliance = Decimal("0.00")
        return self.compliance

    @property
    def has_noncompliance(self):
        return self.missing_rations > 0 or self.undelivered_rations > 0 or not self.menu_matches

    def save(self, *args, **kwargs):
        self.compute_totals()
        super().save(*args, **kwargs)


# ===========================================================================
# 9. CONTROL DE CALIDAD E INOCUIDAD
# ===========================================================================
class PaeChecklist(BaseModel):
    """Lista de verificacion configurable (calidad, inocuidad, supervision)."""

    SCOPE_CHOICES = [
        ("CALIDAD", "Control de calidad e inocuidad"),
        ("VISITA", "Visita de seguimiento"),
        ("DIAGNOSTICO", "Diagnostico de sede"),
        ("OPERADOR", "Evaluacion de operador"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", null=True, blank=True, on_delete=models.CASCADE,
        related_name="checklists",
    )
    code = models.CharField("Codigo", max_length=32, unique=True)
    name = models.CharField("Nombre", max_length=180)
    scope = models.CharField("Ambito", max_length=12, choices=SCOPE_CHOICES, default="CALIDAD")
    description = models.TextField("Descripcion", blank=True)
    version = models.PositiveSmallIntegerField("Version", default=1)
    normative = models.ForeignKey(
        PaeNormative, verbose_name="Norma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="checklists",
    )
    threshold_full = models.DecimalField("Umbral de cumplimiento (%)", max_digits=5, decimal_places=2, default=Decimal("90.00"))
    threshold_partial = models.DecimalField("Umbral de cumplimiento parcial (%)", max_digits=5, decimal_places=2, default=Decimal("70.00"))

    class Meta:
        db_table = "pae_lista_verificacion"
        verbose_name = "Lista de verificacion"
        verbose_name_plural = "Listas de verificacion"
        ordering = ["scope", "name"]

    def __str__(self):
        return f"{self.name} v{self.version}"


class PaeChecklistItem(BaseModel):
    """Criterio verificable dentro de una lista."""

    checklist = models.ForeignKey(
        PaeChecklist, verbose_name="Lista", on_delete=models.CASCADE, related_name="items"
    )
    category = models.ForeignKey(
        PaeCatalog, verbose_name="Categoria", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="checklist_items",
        limit_choices_to={"catalog_type": PaeCatalog.TYPE_CHECK_CATEGORY},
    )
    code = models.CharField("Codigo", max_length=24, blank=True)
    criterion = models.TextField("Criterio")
    weight = models.DecimalField("Peso", max_digits=6, decimal_places=2, default=Decimal("1.00"))
    is_critical = models.BooleanField("Criterio critico", default=False)
    requires_evidence = models.BooleanField("Exige evidencia", default=False)
    normative_reference = models.CharField("Referencia normativa", max_length=120, blank=True)
    order = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        db_table = "pae_lista_item"
        verbose_name = "Criterio de verificacion"
        verbose_name_plural = "Criterios de verificacion"
        ordering = ["category__order", "order", "id"]

    def __str__(self):
        return self.criterion[:80]


class PaeVerification(BaseModel):
    """Aplicacion de una lista de verificacion en una sede y fecha."""

    checklist = models.ForeignKey(
        PaeChecklist, verbose_name="Lista", on_delete=models.PROTECT, related_name="verifications"
    )
    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="verifications"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", on_delete=models.CASCADE, related_name="pae_verifications"
    )
    delivery = models.ForeignKey(
        PaeDelivery, verbose_name="Entrega asociada", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="verifications",
    )
    operator = models.ForeignKey(
        PaeOperator, verbose_name="Operador", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="verifications",
    )
    verification_date = models.DateField("Fecha", default=timezone.localdate, db_index=True)
    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_verifications",
    )
    total_items = models.PositiveSmallIntegerField("Criterios evaluados", default=0, editable=False)
    compliant_items = models.PositiveSmallIntegerField("Criterios que cumplen", default=0, editable=False)
    noncompliant_items = models.PositiveSmallIntegerField("Criterios que no cumplen", default=0, editable=False)
    not_applicable_items = models.PositiveSmallIntegerField("No aplica", default=0, editable=False)
    critical_failures = models.PositiveSmallIntegerField("Fallas criticas", default=0, editable=False)
    score = models.DecimalField("Puntaje (%)", max_digits=5, decimal_places=2, default=Decimal("0.00"), editable=False)
    result = models.CharField("Resultado", max_length=16, choices=COMPLIANCE_RESULT, default="SIN_EVALUAR", editable=False)
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "pae_verificacion"
        verbose_name = "Verificacion"
        verbose_name_plural = "Verificaciones"
        ordering = ["-verification_date"]
        indexes = [models.Index(fields=["vigencia", "campus", "-verification_date"])]

    def __str__(self):
        return f"{self.checklist} - {self.campus} ({self.verification_date})"

    def recalculate(self, save=True):
        """Resultado automatico: CUMPLE / CUMPLE PARCIALMENTE / NO CUMPLE."""
        results = list(self.results.filter(deleted_at__isnull=True).select_related("item"))
        applicable = [row for row in results if row.answer != "NO_APLICA"]

        self.total_items = len(results)
        self.compliant_items = sum(1 for row in results if row.answer == "CUMPLE")
        self.noncompliant_items = sum(1 for row in results if row.answer == "NO_CUMPLE")
        self.not_applicable_items = sum(1 for row in results if row.answer == "NO_APLICA")
        self.critical_failures = sum(
            1 for row in results if row.answer == "NO_CUMPLE" and row.item and row.item.is_critical
        )

        if not applicable:
            self.score = Decimal("0.00")
            self.result = "SIN_EVALUAR"
        else:
            total_weight = sum(Decimal(str(row.item.weight if row.item else 1)) for row in applicable)
            earned = sum(
                Decimal(str(row.item.weight if row.item else 1))
                for row in applicable
                if row.answer == "CUMPLE"
            )
            percentage = (earned / total_weight * 100) if total_weight else Decimal("0")
            self.score = Decimal(str(round(percentage, 2)))

            if self.critical_failures:
                self.result = "NO_CUMPLE"
            elif percentage >= self.checklist.threshold_full:
                self.result = "CUMPLE"
            elif percentage >= self.checklist.threshold_partial:
                self.result = "CUMPLE_PARCIAL"
            else:
                self.result = "NO_CUMPLE"

        if save:
            super().save(update_fields=[
                "total_items", "compliant_items", "noncompliant_items", "not_applicable_items",
                "critical_failures", "score", "result", "updated_at",
            ])
        return self.result


class PaeVerificationResult(BaseModel):
    """Respuesta a un criterio dentro de una verificacion."""

    ANSWER_CHOICES = [
        ("CUMPLE", "Cumple"),
        ("NO_CUMPLE", "No cumple"),
        ("NO_APLICA", "No aplica"),
    ]

    verification = models.ForeignKey(
        PaeVerification, verbose_name="Verificacion", on_delete=models.CASCADE, related_name="results"
    )
    item = models.ForeignKey(
        PaeChecklistItem, verbose_name="Criterio", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="results",
    )
    answer = models.CharField("Respuesta", max_length=12, choices=ANSWER_CHOICES, default="CUMPLE")
    observation = models.TextField("Observacion", blank=True)

    class Meta:
        db_table = "pae_verificacion_resultado"
        verbose_name = "Resultado de verificacion"
        verbose_name_plural = "Resultados de verificacion"
        unique_together = ("verification", "item")
        ordering = ["item__order"]

    def __str__(self):
        return f"{self.item} : {self.answer}"


# ===========================================================================
# 10. VISITAS Y HALLAZGOS
# ===========================================================================
class PaeVisit(BaseModel):
    """Visita de seguimiento, supervision o control a una sede."""

    STATUS_CHOICES = [
        ("PROGRAMADA", "Programada"),
        ("REALIZADA", "Realizada"),
        ("CANCELADA", "Cancelada"),
        ("CERRADA", "Cerrada"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="visits"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", on_delete=models.CASCADE, related_name="pae_visits"
    )
    operator = models.ForeignKey(
        PaeOperator, verbose_name="Operador", null=True, blank=True, on_delete=models.SET_NULL, related_name="visits"
    )
    visit_type = models.ForeignKey(
        PaeCatalog, verbose_name="Tipo de visita", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="visits", limit_choices_to={"catalog_type": PaeCatalog.TYPE_VISIT},
    )
    verification = models.ForeignKey(
        PaeVerification, verbose_name="Lista aplicada", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="visits",
    )
    number = models.CharField("Numero de visita", max_length=32, blank=True, db_index=True)
    visit_date = models.DateField("Fecha", default=timezone.localdate, db_index=True)
    start_time = models.TimeField("Hora de inicio", null=True, blank=True)
    end_time = models.TimeField("Hora de finalizacion", null=True, blank=True)
    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_visits",
    )
    objective = models.TextField("Objetivo", blank=True)
    attendees = models.TextField("Asistentes", blank=True)
    development = models.TextField("Desarrollo de la visita", blank=True)
    conclusions = models.TextField("Conclusiones", blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PROGRAMADA")

    class Meta:
        db_table = "pae_visita"
        verbose_name = "Visita"
        verbose_name_plural = "Visitas y seguimiento"
        ordering = ["-visit_date"]
        indexes = [models.Index(fields=["vigencia", "campus", "-visit_date"])]

    def __str__(self):
        return f"Visita {self.number or self.pk} - {self.campus}"

    def save(self, *args, **kwargs):
        if not self.number:
            year = timezone.localdate().year
            count = PaeVisit.objects.filter(visit_date__year=year).count() + 1
            self.number = f"VIS-{year}-{count:04d}"
        super().save(*args, **kwargs)


class PaeFinding(BaseModel):
    """Hallazgo detectado en una visita o verificacion."""

    SEVERITY_CHOICES = [
        ("LEVE", "Leve"),
        ("MODERADO", "Moderado"),
        ("GRAVE", "Grave"),
        ("CRITICO", "Critico"),
    ]
    STATUS_CHOICES = [
        ("ABIERTO", "Abierto"),
        ("EN_TRATAMIENTO", "En tratamiento"),
        ("VERIFICADO", "Verificado"),
        ("CERRADO", "Cerrado"),
    ]

    visit = models.ForeignKey(
        PaeVisit, verbose_name="Visita", null=True, blank=True, on_delete=models.CASCADE, related_name="findings"
    )
    verification = models.ForeignKey(
        PaeVerification, verbose_name="Verificacion", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="findings",
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", on_delete=models.CASCADE, related_name="pae_findings"
    )
    finding_type = models.ForeignKey(
        PaeCatalog, verbose_name="Tipo de hallazgo", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="findings", limit_choices_to={"catalog_type": PaeCatalog.TYPE_FINDING},
    )
    code = models.CharField("Codigo", max_length=32, blank=True)
    description = models.TextField("Descripcion del hallazgo")
    severity = models.CharField("Severidad", max_length=10, choices=SEVERITY_CHOICES, default="LEVE")
    detected_on = models.DateField("Fecha de deteccion", default=timezone.localdate)
    normative_reference = models.CharField("Referencia normativa", max_length=160, blank=True)
    status = models.CharField("Estado", max_length=14, choices=STATUS_CHOICES, default="ABIERTO")
    closed_at = models.DateTimeField("Cerrado el", null=True, blank=True)

    class Meta:
        db_table = "pae_hallazgo"
        verbose_name = "Hallazgo"
        verbose_name_plural = "Hallazgos"
        ordering = ["-detected_on"]

    def __str__(self):
        return self.description[:80]


# ===========================================================================
# 11. NOVEDADES
# ===========================================================================
class PaeIncident(BaseModel):
    """Novedad reportada durante la operacion del programa."""

    STATUS_CHOICES = [
        ("REPORTADA", "Reportada"),
        ("ASIGNADA", "Asignada"),
        ("EN_INVESTIGACION", "En investigacion"),
        ("EN_CORRECCION", "En correccion"),
        ("SOLUCIONADA", "Solucionada"),
        ("CERRADA", "Cerrada"),
    ]

    TRANSITIONS = {
        "REPORTADA": ["ASIGNADA", "EN_INVESTIGACION"],
        "ASIGNADA": ["EN_INVESTIGACION", "EN_CORRECCION"],
        "EN_INVESTIGACION": ["EN_CORRECCION", "SOLUCIONADA"],
        "EN_CORRECCION": ["SOLUCIONADA"],
        "SOLUCIONADA": ["CERRADA", "EN_CORRECCION"],
        "CERRADA": [],
    }

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="incidents"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", on_delete=models.CASCADE, related_name="pae_incidents"
    )
    delivery = models.ForeignKey(
        PaeDelivery, verbose_name="Entrega relacionada", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="incidents",
    )
    operator = models.ForeignKey(
        PaeOperator, verbose_name="Operador", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="incidents",
    )
    incident_type = models.ForeignKey(
        PaeCatalog, verbose_name="Tipo de novedad", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="incidents", limit_choices_to={"catalog_type": PaeCatalog.TYPE_INCIDENT},
    )
    number = models.CharField("Numero", max_length=32, blank=True, db_index=True)
    reported_on = models.DateField("Fecha del reporte", default=timezone.localdate, db_index=True)
    description = models.TextField("Descripcion")
    priority = models.CharField("Prioridad", max_length=10, choices=PRIORITY_LEVELS, default="MEDIA")
    reported_by = models.ForeignKey(
        "users.User", verbose_name="Reportada por", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_incidents_reported",
    )
    assigned_to = models.ForeignKey(
        "users.User", verbose_name="Responsable asignado", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_incidents_assigned",
    )
    due_date = models.DateField("Fecha limite", null=True, blank=True)
    solution = models.TextField("Solucion aplicada", blank=True)
    solved_at = models.DateTimeField("Solucionada el", null=True, blank=True)
    closed_at = models.DateTimeField("Cerrada el", null=True, blank=True)
    status = models.CharField("Estado", max_length=18, choices=STATUS_CHOICES, default="REPORTADA", db_index=True)

    class Meta:
        db_table = "pae_novedad"
        verbose_name = "Novedad"
        verbose_name_plural = "Novedades"
        ordering = ["-reported_on", "-created_at"]
        indexes = [
            models.Index(fields=["vigencia", "status"]),
            models.Index(fields=["campus", "-reported_on"]),
        ]

    def __str__(self):
        return f"{self.number} - {self.campus}"

    def save(self, *args, **kwargs):
        if not self.number:
            year = timezone.localdate().year
            count = PaeIncident.objects.filter(reported_on__year=year).count() + 1
            self.number = f"NOV-{year}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if not self.due_date or self.status == "CERRADA":
            return False
        return self.due_date < timezone.localdate()

    def allowed_transitions(self):
        return self.TRANSITIONS.get(self.status, [])


class PaeIncidentHistory(BaseModel):
    """Historial de transiciones de una novedad."""

    incident = models.ForeignKey(
        PaeIncident, verbose_name="Novedad", on_delete=models.CASCADE, related_name="history"
    )
    previous_status = models.CharField("Estado anterior", max_length=18, blank=True)
    new_status = models.CharField("Estado nuevo", max_length=18)
    comment = models.TextField("Comentario", blank=True)
    changed_at = models.DateTimeField("Fecha", default=timezone.now)
    changed_by = models.ForeignKey(
        "users.User", verbose_name="Realizado por", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_incident_changes",
    )

    class Meta:
        db_table = "pae_novedad_historial"
        verbose_name = "Historial de novedad"
        verbose_name_plural = "Historial de novedades"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.incident}: {self.previous_status} -> {self.new_status}"


# ===========================================================================
# 12. PLANES DE MEJORAMIENTO
# ===========================================================================
class PaeImprovementAction(BaseModel):
    """Accion correctiva o preventiva derivada de un hallazgo o novedad."""

    STATUS_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("EN_EJECUCION", "En ejecucion"),
        ("VERIFICADA", "Verificada"),
        ("CERRADA", "Cerrada"),
        ("VENCIDA", "Vencida"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="improvement_actions"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_improvement_actions",
    )
    finding = models.ForeignKey(
        PaeFinding, verbose_name="Hallazgo", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="improvement_actions",
    )
    incident = models.ForeignKey(
        PaeIncident, verbose_name="Novedad", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="improvement_actions",
    )
    code = models.CharField("Codigo", max_length=32, blank=True, db_index=True)
    finding_description = models.TextField("Hallazgo / situacion")
    root_cause = models.TextField("Causa raiz", blank=True)
    action = models.TextField("Accion de mejora")
    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_improvement_actions",
    )
    start_date = models.DateField("Fecha inicial", default=timezone.localdate)
    due_date = models.DateField("Fecha limite")
    indicator = models.CharField("Indicador de seguimiento", max_length=200, blank=True)
    goal = models.CharField("Meta", max_length=160, blank=True)
    progress = models.PositiveSmallIntegerField("Avance (%)", default=0, validators=[MinValueValidator(0)])
    requires_evidence = models.BooleanField("Exige evidencia para cerrar", default=True)
    verification_note = models.TextField("Verificacion de eficacia", blank=True)
    verified_by = models.ForeignKey(
        "users.User", verbose_name="Verificada por", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_actions_verified",
    )
    verified_at = models.DateTimeField("Verificada el", null=True, blank=True)
    closed_at = models.DateTimeField("Cerrada el", null=True, blank=True)
    status = models.CharField("Estado", max_length=14, choices=STATUS_CHOICES, default="PENDIENTE", db_index=True)

    class Meta:
        db_table = "pae_accion_correctiva"
        verbose_name = "Accion de mejoramiento"
        verbose_name_plural = "Planes de mejoramiento"
        ordering = ["due_date"]
        indexes = [models.Index(fields=["vigencia", "status"])]

    def __str__(self):
        return f"{self.code} - {self.action[:60]}"

    def save(self, *args, **kwargs):
        if not self.code:
            year = timezone.localdate().year
            count = PaeImprovementAction.objects.filter(created_at__year=year).count() + 1
            self.code = f"PM-{year}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.status in ("CERRADA", "VERIFICADA"):
            return False
        return self.due_date < timezone.localdate()

    @property
    def days_remaining(self):
        return (self.due_date - timezone.localdate()).days


# ===========================================================================
# 13. PQRS Y PARTICIPACION CIUDADANA
# ===========================================================================
class PaePqrs(BaseModel):
    """Peticion, queja, reclamo, sugerencia o felicitacion."""

    KIND_CHOICES = [
        ("PETICION", "Peticion"),
        ("QUEJA", "Queja"),
        ("RECLAMO", "Reclamo"),
        ("SUGERENCIA", "Sugerencia"),
        ("FELICITACION", "Felicitacion"),
    ]
    STATUS_CHOICES = [
        ("RADICADA", "Radicada"),
        ("EN_TRAMITE", "En tramite"),
        ("RESPONDIDA", "Respondida"),
        ("CERRADA", "Cerrada"),
        ("VENCIDA", "Vencida"),
    ]
    CHANNEL_CHOICES = [
        ("PRESENCIAL", "Presencial"),
        ("BUZON", "Buzon"),
        ("TELEFONO", "Telefono"),
        ("CORREO", "Correo electronico"),
        ("PLATAFORMA", "Plataforma"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="pqrs"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_pqrs",
    )
    filing_number = models.CharField("Radicado", max_length=32, blank=True, db_index=True)
    kind = models.CharField("Tipo", max_length=14, choices=KIND_CHOICES, default="PETICION")
    pqrs_type = models.ForeignKey(
        PaeCatalog, verbose_name="Clasificacion", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pqrs", limit_choices_to={"catalog_type": PaeCatalog.TYPE_PQRS},
    )
    channel = models.CharField("Canal", max_length=12, choices=CHANNEL_CHOICES, default="PLATAFORMA")
    filed_on = models.DateField("Fecha de radicacion", default=timezone.localdate, db_index=True)
    applicant_name = models.CharField("Nombre del solicitante", max_length=180, blank=True)
    applicant_document = models.CharField("Documento", max_length=32, blank=True)
    applicant_email = models.EmailField("Correo", blank=True)
    applicant_phone = models.CharField("Telefono", max_length=32, blank=True)
    is_anonymous = models.BooleanField("Anonima", default=False)
    description = models.TextField("Descripcion")
    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_pqrs",
    )
    due_date = models.DateField("Fecha limite de respuesta", null=True, blank=True)
    answer = models.TextField("Respuesta", blank=True)
    answered_on = models.DateField("Fecha de respuesta", null=True, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="RADICADA", db_index=True)

    class Meta:
        db_table = "pae_pqrs"
        verbose_name = "PQRS"
        verbose_name_plural = "PQRS"
        ordering = ["-filed_on"]
        indexes = [models.Index(fields=["vigencia", "status"])]

    def __str__(self):
        return f"{self.filing_number} - {self.get_kind_display()}"

    def save(self, *args, **kwargs):
        if not self.filing_number:
            year = timezone.localdate().year
            count = PaePqrs.objects.filter(filed_on__year=year).count() + 1
            self.filing_number = f"PQRS-{year}-{count:04d}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if not self.due_date or self.status in ("RESPONDIDA", "CERRADA"):
            return False
        return self.due_date < timezone.localdate()


class PaeParticipationMeeting(BaseModel):
    """Reunion de participacion ciudadana / comite de alimentacion escolar."""

    STATUS_CHOICES = [
        ("PROGRAMADA", "Programada"),
        ("REALIZADA", "Realizada"),
        ("CANCELADA", "Cancelada"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="meetings"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_meetings",
    )
    meeting_type = models.ForeignKey(
        PaeCatalog, verbose_name="Tipo de reunion", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="meetings", limit_choices_to={"catalog_type": PaeCatalog.TYPE_MEETING},
    )
    act_number = models.CharField("Numero de acta", max_length=32, blank=True)
    meeting_date = models.DateTimeField("Fecha y hora")
    place = models.CharField("Lugar", max_length=160, blank=True)
    subject = models.CharField("Asunto", max_length=200)
    agenda = models.TextField("Orden del dia", blank=True)
    development = models.TextField("Desarrollo", blank=True)
    agreements = models.TextField("Compromisos y acuerdos", blank=True)
    attendees_count = models.PositiveSmallIntegerField("Numero de asistentes", default=0)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PROGRAMADA")

    class Meta:
        db_table = "pae_participacion"
        verbose_name = "Reunion de participacion"
        verbose_name_plural = "Participacion ciudadana"
        ordering = ["-meeting_date"]

    def __str__(self):
        return f"{self.act_number or 'Acta'} - {self.subject}"


class PaeParticipant(BaseModel):
    """Asistente a una reunion de participacion."""

    ROLE_CHOICES = [
        ("PADRE", "Padre de familia / acudiente"),
        ("ESTUDIANTE", "Estudiante"),
        ("DOCENTE", "Docente"),
        ("DIRECTIVO", "Directivo"),
        ("OPERADOR", "Operador"),
        ("ENTE_TERRITORIAL", "Ente territorial"),
        ("OTRO", "Otro"),
    ]

    meeting = models.ForeignKey(
        PaeParticipationMeeting, verbose_name="Reunion", on_delete=models.CASCADE, related_name="participants"
    )
    full_name = models.CharField("Nombre completo", max_length=180)
    document = models.CharField("Documento", max_length=32, blank=True)
    role = models.CharField("Calidad en que asiste", max_length=18, choices=ROLE_CHOICES, default="PADRE")
    organization = models.CharField("Organizacion", max_length=160, blank=True)
    email = models.EmailField("Correo", blank=True)
    phone = models.CharField("Telefono", max_length=32, blank=True)
    user = models.ForeignKey(
        "users.User", verbose_name="Usuario", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_participations",
    )

    class Meta:
        db_table = "pae_participante"
        verbose_name = "Participante"
        verbose_name_plural = "Participantes"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class PaeCommitment(BaseModel):
    """Compromiso adquirido en una visita o reunion, con seguimiento."""

    STATUS_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("EN_PROCESO", "En proceso"),
        ("CUMPLIDO", "Cumplido"),
        ("INCUMPLIDO", "Incumplido"),
    ]

    visit = models.ForeignKey(
        PaeVisit, verbose_name="Visita", null=True, blank=True, on_delete=models.CASCADE, related_name="commitments"
    )
    meeting = models.ForeignKey(
        PaeParticipationMeeting, verbose_name="Reunion", null=True, blank=True, on_delete=models.CASCADE,
        related_name="commitments",
    )
    description = models.TextField("Compromiso")
    responsible_name = models.CharField("Responsable", max_length=180, blank=True)
    responsible_user = models.ForeignKey(
        "users.User", verbose_name="Usuario responsable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_commitments",
    )
    due_date = models.DateField("Fecha limite", null=True, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PENDIENTE")
    follow_up = models.TextField("Seguimiento", blank=True)
    completed_at = models.DateTimeField("Cumplido el", null=True, blank=True)

    class Meta:
        db_table = "pae_compromiso"
        verbose_name = "Compromiso"
        verbose_name_plural = "Compromisos"
        ordering = ["due_date"]

    def __str__(self):
        return self.description[:80]

    @property
    def is_overdue(self):
        if not self.due_date or self.status == "CUMPLIDO":
            return False
        return self.due_date < timezone.localdate()


# ===========================================================================
# 14. DOCUMENTOS Y EVIDENCIAS
# ===========================================================================
class PaeDocument(BaseModel):
    """
    Repositorio documental del PAE con versionamiento.

    Complementa a core.documents (que genera documentos a partir de plantillas):
    aqui se custodian los archivos soporte del programa.
    """

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("VIGENTE", "Vigente"),
        ("VENCIDO", "Vencido"),
        ("ARCHIVADO", "Archivado"),
    ]

    MODULE_CHOICES = [
        ("CONFIGURACION", "Configuracion"),
        ("DIAGNOSTICO", "Diagnostico"),
        ("PRIORIZACION", "Priorizacion"),
        ("BENEFICIARIOS", "Beneficiarios"),
        ("PLANEACION", "Planeacion"),
        ("MENUS", "Menus"),
        ("OPERADORES", "Operadores"),
        ("CONTRATOS", "Contratos"),
        ("PROGRAMACION", "Programacion"),
        ("ENTREGAS", "Entregas"),
        ("CONTROL", "Control de calidad"),
        ("VISITAS", "Visitas"),
        ("NOVEDADES", "Novedades"),
        ("MEJORAMIENTO", "Planes de mejoramiento"),
        ("PQRS", "PQRS"),
        ("PARTICIPACION", "Participacion ciudadana"),
        ("INFORMES", "Informes"),
        ("OTRO", "Otro"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", null=True, blank=True, on_delete=models.CASCADE,
        related_name="documents",
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_documents",
    )
    document_type = models.ForeignKey(
        PaeCatalog, verbose_name="Tipo de documento", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="documents", limit_choices_to={"catalog_type": PaeCatalog.TYPE_DOCUMENT},
    )
    module = models.CharField("Modulo", max_length=16, choices=MODULE_CHOICES, default="OTRO", db_index=True)
    name = models.CharField("Nombre del documento", max_length=200)
    description = models.TextField("Descripcion", blank=True)
    file = models.FileField("Archivo", upload_to="pae/documentos/%Y/%m/")
    version = models.PositiveSmallIntegerField("Version", default=1)
    parent_version = models.ForeignKey(
        "self", verbose_name="Version anterior", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="new_versions",
    )
    document_date = models.DateField("Fecha del documento", default=timezone.localdate)
    expires_on = models.DateField("Vence el", null=True, blank=True)
    alert_days = models.PositiveSmallIntegerField("Alertar dias antes", default=30)
    responsible = models.ForeignKey(
        "users.User", verbose_name="Responsable", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_documents",
    )
    operator = models.ForeignKey(
        PaeOperator, verbose_name="Operador", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="documents",
    )
    contract = models.ForeignKey(
        PaeContract, verbose_name="Contrato", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="documents",
    )
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="VIGENTE")
    file_size = models.PositiveIntegerField("Tamano (bytes)", default=0, editable=False)
    content_type = models.CharField("Tipo MIME", max_length=120, blank=True, editable=False)
    downloads = models.PositiveIntegerField("Descargas", default=0, editable=False)

    class Meta:
        db_table = "pae_documento"
        verbose_name = "Documento PAE"
        verbose_name_plural = "Documentos PAE"
        ordering = ["-document_date", "name"]
        indexes = [models.Index(fields=["module", "status"])]

    def __str__(self):
        return f"{self.name} v{self.version}"

    @property
    def days_to_expire(self):
        if not self.expires_on:
            return None
        return (self.expires_on - timezone.localdate()).days

    @property
    def is_expiring(self):
        days = self.days_to_expire
        return days is not None and 0 <= days <= self.alert_days

    @property
    def is_expired(self):
        days = self.days_to_expire
        return days is not None and days < 0

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "size"):
            try:
                self.file_size = self.file.size
            except (OSError, ValueError):
                pass
        if self.expires_on and self.expires_on < timezone.localdate() and self.status == "VIGENTE":
            self.status = "VENCIDO"
        super().save(*args, **kwargs)


class PaeEvidence(BaseModel):
    """
    Evidencia adjunta (fotografia, acta, registro) asociada a cualquier
    registro del modulo mediante una referencia ligera modulo + identificador.
    """

    KIND_CHOICES = [
        ("FOTOGRAFIA", "Fotografia"),
        ("ACTA", "Acta"),
        ("PLANILLA", "Planilla"),
        ("REGISTRO", "Registro"),
        ("SOPORTE", "Soporte"),
        ("OTRO", "Otro"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", null=True, blank=True, on_delete=models.CASCADE,
        related_name="evidences",
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_evidences",
    )
    module = models.CharField("Modulo", max_length=16, choices=PaeDocument.MODULE_CHOICES, default="OTRO", db_index=True)
    reference_id = models.PositiveIntegerField("Identificador del registro", null=True, blank=True, db_index=True)
    reference_label = models.CharField("Registro", max_length=200, blank=True)
    kind = models.CharField("Tipo de evidencia", max_length=12, choices=KIND_CHOICES, default="FOTOGRAFIA")
    name = models.CharField("Nombre", max_length=200)
    description = models.TextField("Descripcion", blank=True)
    file = models.FileField("Archivo", upload_to="pae/evidencias/%Y/%m/")
    captured_at = models.DateTimeField("Fecha de captura", default=timezone.now)
    file_size = models.PositiveIntegerField("Tamano (bytes)", default=0, editable=False)

    class Meta:
        db_table = "pae_evidencia"
        verbose_name = "Evidencia"
        verbose_name_plural = "Evidencias"
        ordering = ["-captured_at"]
        indexes = [models.Index(fields=["module", "reference_id"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "size"):
            try:
                self.file_size = self.file.size
            except (OSError, ValueError):
                pass
        super().save(*args, **kwargs)


# ===========================================================================
# 15. INDICADORES E INFORMES
# ===========================================================================
class PaeIndicator(BaseModel):
    """Indicador calculado y almacenado para el tablero y los informes."""

    PERIOD_CHOICES = [
        ("DIARIO", "Diario"),
        ("SEMANAL", "Semanal"),
        ("MENSUAL", "Mensual"),
        ("VIGENCIA", "Vigencia"),
    ]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", on_delete=models.CASCADE, related_name="indicators"
    )
    campus = models.ForeignKey(
        "institutions.Campus", verbose_name="Sede", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_indicators",
    )
    code = models.CharField("Codigo", max_length=48, db_index=True)
    name = models.CharField("Indicador", max_length=180)
    period_type = models.CharField("Periodicidad", max_length=10, choices=PERIOD_CHOICES, default="MENSUAL")
    period_label = models.CharField("Periodo", max_length=40, blank=True)
    period_start = models.DateField("Desde", null=True, blank=True)
    period_end = models.DateField("Hasta", null=True, blank=True)
    value = models.DecimalField("Valor", max_digits=14, decimal_places=2, default=Decimal("0.00"))
    goal = models.DecimalField("Meta", max_digits=14, decimal_places=2, default=Decimal("0.00"))
    unit = models.CharField("Unidad", max_length=20, blank=True)
    calculated_at = models.DateTimeField("Calculado el", default=timezone.now)

    class Meta:
        db_table = "pae_indicador"
        verbose_name = "Indicador PAE"
        verbose_name_plural = "Indicadores PAE"
        unique_together = ("vigencia", "campus", "code", "period_label")
        ordering = ["code", "-period_start"]

    def __str__(self):
        return f"{self.name} ({self.period_label}): {self.value}"

    @property
    def achievement(self):
        if not self.goal:
            return 0
        return round(float(self.value) / float(self.goal) * 100, 2)


class PaeReport(BaseModel):
    """Historial de informes generados desde el modulo."""

    FORMAT_CHOICES = [("XLSX", "Excel"), ("CSV", "CSV"), ("PDF", "PDF"), ("HTML", "Pantalla")]

    vigencia = models.ForeignKey(
        PaeVigencia, verbose_name="Vigencia", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="reports",
    )
    code = models.CharField("Codigo del reporte", max_length=48, db_index=True)
    name = models.CharField("Nombre", max_length=180)
    parameters = models.JSONField("Parametros", default=dict, blank=True)
    output_format = models.CharField("Formato", max_length=6, choices=FORMAT_CHOICES, default="XLSX")
    rows = models.PositiveIntegerField("Registros", default=0)
    generated_at = models.DateTimeField("Generado el", default=timezone.now)
    generated_by = models.ForeignKey(
        "users.User", verbose_name="Generado por", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pae_reports",
    )
    file = models.FileField("Archivo", upload_to="pae/informes/%Y/%m/", null=True, blank=True)

    class Meta:
        db_table = "pae_reporte"
        verbose_name = "Informe PAE"
        verbose_name_plural = "Informes PAE"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.name} - {self.generated_at:%Y-%m-%d %H:%M}"
