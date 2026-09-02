"""
Gestion de estudiantes: registro, acudientes, matricula, admisiones,
inscripciones, hoja de vida y certificados.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel
from core.users.models import DOCUMENT_TYPES, GENDER_CHOICES

BLOOD_TYPES = [
    ("O+", "O+"), ("O-", "O-"), ("A+", "A+"), ("A-", "A-"),
    ("B+", "B+"), ("B-", "B-"), ("AB+", "AB+"), ("AB-", "AB-"),
]

STRATUM_CHOICES = [(i, f"Estrato {i}") for i in range(1, 7)] + [(0, "No aplica")]


class Guardian(BaseModel):
    """Acudiente / padre de familia."""

    RELATION_CHOICES = [
        ("PADRE", "Padre"),
        ("MADRE", "Madre"),
        ("ABUELO", "Abuelo(a)"),
        ("TIO", "Tio(a)"),
        ("HERMANO", "Hermano(a)"),
        ("TUTOR", "Tutor legal"),
        ("OTRO", "Otro"),
    ]

    user = models.OneToOneField(
        "users.User",
        verbose_name="Usuario de acceso",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="guardian_profile",
    )
    document_type = models.CharField("Tipo de documento", max_length=8, choices=DOCUMENT_TYPES, default="CC")
    document_number = models.CharField("Numero de documento", max_length=32, unique=True)
    first_name = models.CharField("Nombres", max_length=120)
    last_name = models.CharField("Apellidos", max_length=120)
    relation = models.CharField("Parentesco", max_length=12, choices=RELATION_CHOICES, default="PADRE")
    email = models.EmailField("Correo electronico", blank=True)
    phone = models.CharField("Telefono", max_length=32, blank=True)
    mobile = models.CharField("Celular", max_length=32, blank=True)
    address = models.CharField("Direccion", max_length=200, blank=True)
    occupation = models.CharField("Ocupacion", max_length=120, blank=True)
    workplace = models.CharField("Lugar de trabajo", max_length=160, blank=True)
    education_level = models.CharField("Nivel educativo", max_length=80, blank=True)
    lives_with_student = models.BooleanField("Convive con el estudiante", default=True)

    class Meta:
        db_table = "student_guardian"
        verbose_name = "Acudiente"
        verbose_name_plural = "Acudientes"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Student(BaseModel):
    STATUS_CHOICES = [
        ("ACTIVO", "Activo"),
        ("RETIRADO", "Retirado"),
        ("EGRESADO", "Egresado"),
        ("TRASLADADO", "Trasladado"),
        ("SUSPENDIDO", "Suspendido"),
        ("INACTIVO", "Inactivo"),
    ]

    user = models.OneToOneField(
        "users.User",
        verbose_name="Usuario de acceso",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_profile",
    )
    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="students"
    )

    student_code = models.CharField("Codigo del estudiante", max_length=32, unique=True, db_index=True)
    document_type = models.CharField("Tipo de documento", max_length=8, choices=DOCUMENT_TYPES, default="TI")
    document_number = models.CharField("Numero de documento", max_length=32, unique=True, db_index=True)
    document_city = models.CharField("Lugar de expedicion", max_length=120, blank=True)
    first_name = models.CharField("Nombres", max_length=120)
    last_name = models.CharField("Apellidos", max_length=120)
    birth_date = models.DateField("Fecha de nacimiento", null=True, blank=True)
    birth_place = models.CharField("Lugar de nacimiento", max_length=160, blank=True)
    gender = models.CharField("Genero", max_length=1, choices=GENDER_CHOICES, default="N")
    photo = models.ImageField("Fotografia", upload_to="students/photos/", null=True, blank=True)

    email = models.EmailField("Correo electronico", blank=True)
    phone = models.CharField("Telefono", max_length=32, blank=True)
    mobile = models.CharField("Celular", max_length=32, blank=True)
    address = models.CharField("Direccion de residencia", max_length=200, blank=True)
    neighborhood = models.CharField("Barrio", max_length=120, blank=True)
    city = models.CharField("Ciudad", max_length=120, blank=True)
    department = models.CharField("Departamento", max_length=120, blank=True)
    stratum = models.PositiveSmallIntegerField("Estrato", choices=STRATUM_CHOICES, default=0)

    blood_type = models.CharField("Grupo sanguineo", max_length=4, choices=BLOOD_TYPES, blank=True)
    eps = models.CharField("EPS", max_length=120, blank=True)
    disability = models.CharField("Condicion de discapacidad", max_length=160, blank=True)
    allergies = models.TextField("Alergias", blank=True)
    medical_notes = models.TextField("Observaciones medicas", blank=True)
    emergency_contact = models.CharField("Contacto de emergencia", max_length=160, blank=True)
    emergency_phone = models.CharField("Telefono de emergencia", max_length=32, blank=True)

    ethnicity = models.CharField("Etnia", max_length=120, blank=True)
    displaced = models.BooleanField("Poblacion desplazada", default=False)
    sisben = models.CharField("SISBEN", max_length=40, blank=True)
    religion = models.CharField("Religion", max_length=80, blank=True)

    previous_school = models.CharField("Institucion anterior", max_length=200, blank=True)
    entry_date = models.DateField("Fecha de ingreso", null=True, blank=True)
    exit_date = models.DateField("Fecha de retiro", null=True, blank=True)
    exit_reason = models.CharField("Motivo de retiro", max_length=200, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="ACTIVO", db_index=True)

    guardians = models.ManyToManyField(
        Guardian, through="StudentGuardian", verbose_name="Acudientes", related_name="students"
    )
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "student"
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["document_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}".strip()

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = timezone.localdate()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    @property
    def current_enrollment(self):
        return (
            self.enrollments.filter(status="ACTIVA", deleted_at__isnull=True)
            .select_related("group", "group__grade", "school_year")
            .order_by("-school_year__year")
            .first()
        )

    @property
    def current_group(self):
        enrollment = self.current_enrollment
        return enrollment.group if enrollment else None

    @property
    def main_guardian(self):
        link = self.guardian_links.filter(is_primary=True).select_related("guardian").first()
        return link.guardian if link else None

    def save(self, *args, **kwargs):
        if not self.student_code:
            year = timezone.localdate().year
            last = Student.objects.filter(student_code__startswith=str(year)).count() + 1
            self.student_code = f"{year}{last:05d}"
        super().save(*args, **kwargs)


class StudentGuardian(BaseModel):
    student = models.ForeignKey(
        Student, verbose_name="Estudiante", on_delete=models.CASCADE, related_name="guardian_links"
    )
    guardian = models.ForeignKey(
        Guardian, verbose_name="Acudiente", on_delete=models.CASCADE, related_name="student_links"
    )
    is_primary = models.BooleanField("Acudiente principal", default=False)
    is_financial = models.BooleanField("Responsable financiero", default=False)
    can_pickup = models.BooleanField("Autorizado a recoger", default=True)
    notes = models.CharField("Observaciones", max_length=240, blank=True)

    class Meta:
        db_table = "student_guardian_link"
        verbose_name = "Acudiente del estudiante"
        verbose_name_plural = "Acudientes del estudiante"
        unique_together = ("student", "guardian")
        ordering = ["-is_primary"]

    def __str__(self):
        return f"{self.guardian} -> {self.student}"


class Enrollment(BaseModel):
    """Matricula del estudiante en un grupo y ano lectivo."""

    STATUS_CHOICES = [
        ("ACTIVA", "Activa"),
        ("RETIRADA", "Retirada"),
        ("TRASLADADA", "Trasladada"),
        ("CANCELADA", "Cancelada"),
        ("FINALIZADA", "Finalizada"),
    ]
    TYPE_CHOICES = [
        ("NUEVO", "Estudiante nuevo"),
        ("ANTIGUO", "Estudiante antiguo"),
        ("REINTEGRO", "Reintegro"),
        ("TRASLADO", "Traslado"),
    ]

    student = models.ForeignKey(
        Student, verbose_name="Estudiante", on_delete=models.CASCADE, related_name="enrollments"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.PROTECT, related_name="enrollments"
    )
    group = models.ForeignKey(
        "academic.Group", verbose_name="Grupo", on_delete=models.PROTECT, related_name="enrollments"
    )
    enrollment_number = models.CharField("Numero de matricula", max_length=32, blank=True, db_index=True)
    enrollment_date = models.DateField("Fecha de matricula", default=timezone.localdate)
    enrollment_type = models.CharField("Tipo de matricula", max_length=12, choices=TYPE_CHOICES, default="NUEVO")
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="ACTIVA", db_index=True)
    folio = models.CharField("Folio", max_length=32, blank=True)
    book = models.CharField("Libro", max_length=32, blank=True)
    withdrawal_date = models.DateField("Fecha de retiro", null=True, blank=True)
    withdrawal_reason = models.CharField("Motivo de retiro", max_length=240, blank=True)
    is_repeating = models.BooleanField("Repitente", default=False)
    scholarship = models.BooleanField("Becado", default=False)
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "student_enrollment"
        verbose_name = "Matricula"
        verbose_name_plural = "Matriculas"
        unique_together = ("student", "school_year")
        ordering = ["-school_year__year", "group__code"]
        indexes = [models.Index(fields=["school_year", "status"])]

    def __str__(self):
        return f"{self.student} - {self.group} ({self.school_year})"

    def save(self, *args, **kwargs):
        if not self.enrollment_number:
            year = self.school_year.year if self.school_year_id else timezone.localdate().year
            count = Enrollment.objects.filter(school_year=self.school_year).count() + 1
            self.enrollment_number = f"MT-{year}-{count:05d}"
        super().save(*args, **kwargs)

    def withdraw(self, reason="", date=None):
        self.status = "RETIRADA"
        self.withdrawal_date = date or timezone.localdate()
        self.withdrawal_reason = reason
        self.save(update_fields=["status", "withdrawal_date", "withdrawal_reason"])
        self.student.status = "RETIRADO"
        self.student.exit_date = self.withdrawal_date
        self.student.exit_reason = reason
        self.student.save(update_fields=["status", "exit_date", "exit_reason"])


class Admission(BaseModel):
    """Proceso de admision de aspirantes."""

    STATUS_CHOICES = [
        ("RECIBIDA", "Solicitud recibida"),
        ("EN_ESTUDIO", "En estudio"),
        ("ENTREVISTA", "Entrevista programada"),
        ("APROBADA", "Aprobada"),
        ("RECHAZADA", "Rechazada"),
        ("MATRICULADA", "Matriculada"),
    ]

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="admissions"
    )
    grade = models.ForeignKey(
        "academic.Grade", verbose_name="Grado solicitado", on_delete=models.PROTECT, related_name="admissions"
    )
    applicant_document_type = models.CharField("Tipo de documento", max_length=8, choices=DOCUMENT_TYPES, default="TI")
    applicant_document = models.CharField("Documento del aspirante", max_length=32, db_index=True)
    applicant_first_name = models.CharField("Nombres del aspirante", max_length=120)
    applicant_last_name = models.CharField("Apellidos del aspirante", max_length=120)
    birth_date = models.DateField("Fecha de nacimiento", null=True, blank=True)
    gender = models.CharField("Genero", max_length=1, choices=GENDER_CHOICES, default="N")
    guardian_name = models.CharField("Nombre del acudiente", max_length=160)
    guardian_document = models.CharField("Documento del acudiente", max_length=32, blank=True)
    guardian_email = models.EmailField("Correo del acudiente")
    guardian_phone = models.CharField("Telefono del acudiente", max_length=32)
    previous_school = models.CharField("Institucion anterior", max_length=200, blank=True)
    application_date = models.DateField("Fecha de solicitud", default=timezone.localdate)
    interview_date = models.DateTimeField("Fecha de entrevista", null=True, blank=True)
    score = models.DecimalField("Puntaje", max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="RECIBIDA", db_index=True)
    approved_by = models.ForeignKey(
        "users.User", verbose_name="Aprobado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_admissions"
    )
    approved_at = models.DateTimeField("Aprobado el", null=True, blank=True)
    student = models.ForeignKey(
        Student, verbose_name="Estudiante generado", null=True, blank=True, on_delete=models.SET_NULL, related_name="admissions"
    )
    observations = models.TextField("Observaciones", blank=True)

    class Meta:
        db_table = "student_admission"
        verbose_name = "Admision"
        verbose_name_plural = "Admisiones"
        ordering = ["-application_date"]

    def __str__(self):
        return f"{self.applicant_first_name} {self.applicant_last_name} - {self.grade}"

    @property
    def applicant_name(self):
        return f"{self.applicant_first_name} {self.applicant_last_name}".strip()


class Inscription(BaseModel):
    """Preinscripcion publica de aspirantes (formulario web)."""

    STATUS_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("CONTACTADO", "Contactado"),
        ("CONVERTIDA", "Convertida en admision"),
        ("DESCARTADA", "Descartada"),
    ]

    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", on_delete=models.CASCADE, related_name="inscriptions"
    )
    grade = models.ForeignKey(
        "academic.Grade", verbose_name="Grado de interes", on_delete=models.PROTECT, related_name="inscriptions"
    )
    full_name = models.CharField("Nombre del aspirante", max_length=180)
    document = models.CharField("Documento", max_length=32, blank=True)
    birth_date = models.DateField("Fecha de nacimiento", null=True, blank=True)
    guardian_name = models.CharField("Nombre del acudiente", max_length=180)
    email = models.EmailField("Correo electronico")
    phone = models.CharField("Telefono", max_length=32)
    message = models.TextField("Mensaje", blank=True)
    source = models.CharField("Origen", max_length=60, default="WEB")
    status = models.CharField("Estado", max_length=12, choices=STATUS_CHOICES, default="PENDIENTE")
    admission = models.ForeignKey(
        Admission, verbose_name="Admision", null=True, blank=True, on_delete=models.SET_NULL, related_name="inscriptions"
    )

    class Meta:
        db_table = "student_inscription"
        verbose_name = "Inscripcion"
        verbose_name_plural = "Inscripciones"
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name


class StudentDocument(BaseModel):
    """Documentos anexos de la hoja de vida del estudiante."""

    DOCUMENT_KINDS = [
        ("REGISTRO_CIVIL", "Registro civil"),
        ("DOCUMENTO_IDENTIDAD", "Documento de identidad"),
        ("CERTIFICADO_MEDICO", "Certificado medico"),
        ("BOLETIN_ANTERIOR", "Boletin anterior"),
        ("PAZ_Y_SALVO", "Paz y salvo"),
        ("FOTO", "Fotografia"),
        ("CONTRATO", "Contrato de matricula"),
        ("OTRO", "Otro"),
    ]

    student = models.ForeignKey(
        Student, verbose_name="Estudiante", on_delete=models.CASCADE, related_name="documents"
    )
    kind = models.CharField("Tipo de documento", max_length=24, choices=DOCUMENT_KINDS, default="OTRO")
    name = models.CharField("Nombre", max_length=160)
    file = models.FileField("Archivo", upload_to="students/documents/%Y/%m/")
    is_verified = models.BooleanField("Verificado", default=False)
    verified_by = models.ForeignKey(
        "users.User", verbose_name="Verificado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_student_documents"
    )
    notes = models.CharField("Observaciones", max_length=240, blank=True)

    class Meta:
        db_table = "student_document"
        verbose_name = "Documento del estudiante"
        verbose_name_plural = "Documentos del estudiante"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.student}"


class StudentCertificate(BaseModel):
    """Certificados emitidos al estudiante (estudio, notas, paz y salvo)."""

    KIND_CHOICES = [
        ("ESTUDIO", "Certificado de estudio"),
        ("NOTAS", "Certificado de notas"),
        ("CONDUCTA", "Certificado de conducta"),
        ("PAZ_Y_SALVO", "Paz y salvo"),
        ("RETIRO", "Constancia de retiro"),
        ("GRADO", "Acta de grado"),
        ("DIPLOMA", "Diploma"),
    ]

    student = models.ForeignKey(
        Student, verbose_name="Estudiante", on_delete=models.CASCADE, related_name="certificates"
    )
    school_year = models.ForeignKey(
        "academic.SchoolYear", verbose_name="Ano lectivo", null=True, blank=True, on_delete=models.SET_NULL, related_name="certificates"
    )
    kind = models.CharField("Tipo de certificado", max_length=16, choices=KIND_CHOICES)
    consecutive = models.CharField("Consecutivo", max_length=32, blank=True, db_index=True)
    issued_at = models.DateTimeField("Emitido el", default=timezone.now)
    issued_by = models.ForeignKey(
        "users.User", verbose_name="Emitido por", null=True, blank=True, on_delete=models.SET_NULL, related_name="issued_certificates"
    )
    purpose = models.CharField("Dirigido a", max_length=200, blank=True)
    content = models.TextField("Contenido generado", blank=True)
    file = models.FileField("Archivo PDF", upload_to="students/certificates/%Y/", null=True, blank=True)
    verification_code = models.CharField("Codigo de verificacion", max_length=40, blank=True, db_index=True)

    class Meta:
        db_table = "student_certificate"
        verbose_name = "Certificado"
        verbose_name_plural = "Certificados"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.get_kind_display()} - {self.student}"

    def save(self, *args, **kwargs):
        if not self.consecutive:
            year = timezone.localdate().year
            count = StudentCertificate.objects.filter(issued_at__year=year).count() + 1
            self.consecutive = f"CE-{year}-{count:05d}"
        if not self.verification_code:
            import secrets

            self.verification_code = secrets.token_hex(8).upper()
        super().save(*args, **kwargs)
