"""
Extensiones: constructor de formularios dinamicos y espacios virtuales.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from config.models_base import BaseModel


class FormDefinition(BaseModel):
    """Formulario dinamico configurable por la institucion."""

    STATUS_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("PUBLICADO", "Publicado"),
        ("CERRADO", "Cerrado"),
    ]
    AUDIENCE_CHOICES = [
        ("PUBLICO", "Publico (sin autenticacion)"),
        ("ESTUDIANTES", "Estudiantes"),
        ("DOCENTES", "Docentes"),
        ("ACUDIENTES", "Acudientes"),
        ("INTERNO", "Usuarios autenticados"),
    ]

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="forms"
    )
    slug = models.SlugField("Identificador URL", max_length=80, unique=True)
    title = models.CharField("Titulo", max_length=200)
    description = models.TextField("Descripcion", blank=True)
    audience = models.CharField("Dirigido a", max_length=12, choices=AUDIENCE_CHOICES, default="INTERNO")
    status = models.CharField("Estado", max_length=10, choices=STATUS_CHOICES, default="BORRADOR")
    opens_at = models.DateTimeField("Disponible desde", null=True, blank=True)
    closes_at = models.DateTimeField("Disponible hasta", null=True, blank=True)
    allow_multiple = models.BooleanField("Permite multiples respuestas", default=False)
    notify_email = models.EmailField("Notificar a", blank=True)
    success_message = models.CharField(
        "Mensaje de confirmacion", max_length=240, default="Su respuesta fue registrada correctamente."
    )
    submissions_count = models.PositiveIntegerField("Respuestas", default=0)

    class Meta:
        db_table = "extension_form"
        verbose_name = "Formulario"
        verbose_name_plural = "Formularios"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        if self.status != "PUBLICADO":
            return False
        now = timezone.now()
        if self.opens_at and now < self.opens_at:
            return False
        if self.closes_at and now > self.closes_at:
            return False
        return True


class FormField(BaseModel):
    TYPE_CHOICES = [
        ("text", "Texto corto"),
        ("textarea", "Texto largo"),
        ("number", "Numero"),
        ("email", "Correo electronico"),
        ("date", "Fecha"),
        ("time", "Hora"),
        ("select", "Lista desplegable"),
        ("radio", "Opcion unica"),
        ("checkbox", "Casillas multiples"),
        ("file", "Archivo"),
        ("rating", "Valoracion 1-5"),
        ("section", "Titulo de seccion"),
    ]

    form = models.ForeignKey(FormDefinition, verbose_name="Formulario", on_delete=models.CASCADE, related_name="fields")
    key = models.CharField("Clave", max_length=60)
    label = models.CharField("Etiqueta", max_length=200)
    field_type = models.CharField("Tipo de campo", max_length=12, choices=TYPE_CHOICES, default="text")
    placeholder = models.CharField("Texto de ayuda", max_length=160, blank=True)
    help_text = models.CharField("Descripcion", max_length=240, blank=True)
    options = models.JSONField("Opciones", default=list, blank=True)
    required = models.BooleanField("Obligatorio", default=False)
    order = models.PositiveSmallIntegerField("Orden", default=0)
    width = models.CharField(
        "Ancho", max_length=8, choices=[("full", "Completo"), ("half", "Mitad"), ("third", "Un tercio")], default="full"
    )

    class Meta:
        db_table = "extension_form_field"
        verbose_name = "Campo del formulario"
        verbose_name_plural = "Campos del formulario"
        unique_together = ("form", "key")
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class FormSubmission(BaseModel):
    form = models.ForeignKey(
        FormDefinition, verbose_name="Formulario", on_delete=models.CASCADE, related_name="submissions"
    )
    user = models.ForeignKey(
        "users.User", verbose_name="Usuario", null=True, blank=True, on_delete=models.SET_NULL, related_name="form_submissions"
    )
    data = models.JSONField("Respuestas", default=dict)
    submitted_at = models.DateTimeField("Enviado el", default=timezone.now)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    reviewed = models.BooleanField("Revisado", default=False)
    reviewed_by = models.ForeignKey(
        "users.User", verbose_name="Revisado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_submissions"
    )
    notes = models.TextField("Notas internas", blank=True)

    class Meta:
        db_table = "extension_form_submission"
        verbose_name = "Respuesta de formulario"
        verbose_name_plural = "Respuestas de formularios"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.form} - {self.submitted_at:%Y-%m-%d %H:%M}"


class VirtualSpace(BaseModel):
    """Espacio virtual: enlace a plataformas externas o recursos institucionales."""

    KIND_CHOICES = [
        ("VIDEOCONFERENCIA", "Videoconferencia"),
        ("BIBLIOTECA", "Biblioteca digital"),
        ("PLATAFORMA", "Plataforma externa"),
        ("REPOSITORIO", "Repositorio"),
        ("APLICACION", "Aplicacion institucional"),
    ]

    institution = models.ForeignKey(
        "institutions.Institution", verbose_name="Institucion", on_delete=models.CASCADE, related_name="virtual_spaces"
    )
    name = models.CharField("Nombre", max_length=180)
    description = models.TextField("Descripcion", blank=True)
    kind = models.CharField("Tipo", max_length=18, choices=KIND_CHOICES, default="PLATAFORMA")
    url = models.URLField("Enlace")
    icon = models.CharField("Icono", max_length=40, default="external")
    color = models.CharField("Color", max_length=20, default="#0EA5E9")
    audience = models.CharField(
        "Dirigido a",
        max_length=12,
        choices=[
            ("TODOS", "Toda la comunidad"),
            ("ESTUDIANTES", "Estudiantes"),
            ("DOCENTES", "Docentes"),
            ("ACUDIENTES", "Acudientes"),
        ],
        default="TODOS",
    )
    open_in_new_tab = models.BooleanField("Abrir en nueva pestana", default=True)
    order = models.PositiveSmallIntegerField("Orden", default=0)
    clicks = models.PositiveIntegerField("Accesos", default=0)

    class Meta:
        db_table = "extension_virtual_space"
        verbose_name = "Espacio virtual"
        verbose_name_plural = "Espacios virtuales"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name
