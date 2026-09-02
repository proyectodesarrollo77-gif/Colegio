"""
Documentos institucionales: plantillas configurables y emision/impresion.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class DocumentTemplate(BaseModel):
    """
    Plantilla de documento institucional con variables dinamicas.

    Variables disponibles (se reemplazan al generar):
      {{estudiante}} {{documento}} {{grado}} {{grupo}} {{ano}} {{fecha}}
      {{institucion}} {{rector}} {{ciudad}} {{consecutivo}} {{acudiente}}
    """

    KIND_CHOICES = [
        ("CERTIFICADO", "Certificado"),
        ("CONSTANCIA", "Constancia"),
        ("ACTA", "Acta"),
        ("DIPLOMA", "Diploma"),
        ("CIRCULAR", "Circular"),
        ("CONTRATO", "Contrato de matricula"),
        ("PAZ_Y_SALVO", "Paz y salvo"),
        ("CARNET", "Carne estudiantil"),
        ("OTRO", "Otro"),
    ]

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="document_templates"
    )
    code = models.CharField("Codigo", max_length=32, unique=True)
    name = models.CharField("Nombre del documento", max_length=180)
    kind = models.CharField("Tipo", max_length=14, choices=KIND_CHOICES, default="CERTIFICADO")
    header = models.ForeignKey(
        "configuration.ReportHeader",
        verbose_name="Encabezado",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="document_templates",
    )
    body = models.TextField("Cuerpo del documento (HTML)", blank=True)
    footer = models.TextField("Pie del documento", blank=True)
    signatures = models.JSONField("Firmas", default=list, blank=True)
    paper_size = models.CharField(
        "Tamano", max_length=10, choices=[("A4", "A4"), ("LETTER", "Carta"), ("LEGAL", "Oficio")], default="LETTER"
    )
    orientation = models.CharField(
        "Orientacion", max_length=1, choices=[("P", "Vertical"), ("L", "Horizontal")], default="P"
    )
    requires_consecutive = models.BooleanField("Usa consecutivo", default=True)
    consecutive_prefix = models.CharField("Prefijo del consecutivo", max_length=16, blank=True)
    next_consecutive = models.PositiveIntegerField("Siguiente consecutivo", default=1)
    requires_approval = models.BooleanField("Requiere aprobacion", default=False)
    show_qr = models.BooleanField("Incluir codigo QR de verificacion", default=True)

    class Meta:
        db_table = "document_template"
        verbose_name = "Plantilla de documento"
        verbose_name_plural = "Plantillas de documentos"
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name

    def build_consecutive(self):
        if not self.requires_consecutive:
            return ""
        value = f"{self.consecutive_prefix or self.code}-{self.next_consecutive:05d}"
        self.next_consecutive += 1
        self.save(update_fields=["next_consecutive"])
        return value

    def render(self, context: dict) -> str:
        content = self.body or ""
        for key, value in context.items():
            content = content.replace("{{" + key + "}}", str(value if value is not None else ""))
        return content


class DocumentIssue(BaseModel):
    """Documento emitido a partir de una plantilla."""

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("EMITIDO", "Emitido"),
        ("APROBADO", "Aprobado"),
        ("ANULADO", "Anulado"),
    ]

    template = models.ForeignKey(
        DocumentTemplate, verbose_name="Plantilla", on_delete=models.PROTECT, related_name="issues"
    )
    student = models.ForeignKey(
        "students.Student", verbose_name="Estudiante", null=True, blank=True, on_delete=models.SET_NULL, related_name="document_issues"
    )
    teacher = models.ForeignKey(
        "teachers.Teacher", verbose_name="Docente", null=True, blank=True, on_delete=models.SET_NULL, related_name="document_issues"
    )
    consecutive = models.CharField("Consecutivo", max_length=40, blank=True, db_index=True)
    title = models.CharField("Titulo", max_length=200)
    content = models.TextField("Contenido generado", blank=True)
    context_data = models.JSONField("Datos del contexto", default=dict, blank=True)
    issued_at = models.DateTimeField("Emitido el", default=timezone.now)
    issued_by = models.ForeignKey(
        "users.User", verbose_name="Emitido por", null=True, blank=True, on_delete=models.SET_NULL, related_name="issued_documents"
    )
    status = models.CharField("Estado", max_length=10, choices=STATUS_CHOICES, default="EMITIDO")
    approved_by = models.ForeignKey(
        "users.User", verbose_name="Aprobado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_documents"
    )
    approved_at = models.DateTimeField("Aprobado el", null=True, blank=True)
    verification_code = models.CharField("Codigo de verificacion", max_length=40, blank=True, db_index=True)
    file = models.FileField("Archivo", upload_to="documents/%Y/%m/", null=True, blank=True)
    print_count = models.PositiveSmallIntegerField("Impresiones", default=0)

    class Meta:
        db_table = "document_issue"
        verbose_name = "Documento emitido"
        verbose_name_plural = "Documentos emitidos"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.title} ({self.consecutive})"

    def save(self, *args, **kwargs):
        if not self.verification_code:
            import secrets

            self.verification_code = secrets.token_hex(8).upper()
        super().save(*args, **kwargs)
