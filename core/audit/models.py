"""Bitacora de auditoria de PL_SGE."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from config.models_base import TimeStampedModel


class AuditLog(TimeStampedModel):
    ACTION_CHOICES = [
        ("CREATE", "Creacion"),
        ("UPDATE", "Modificacion"),
        ("DELETE", "Eliminacion"),
        ("VIEW", "Consulta"),
        ("EXPORT", "Exportacion"),
        ("APPROVE", "Aprobacion"),
        ("TOGGLE", "Cambio de estado"),
        ("LOGIN", "Inicio de sesion"),
        ("LOGOUT", "Cierre de sesion"),
        ("ERROR", "Error"),
        ("PROCESS", "Proceso academico"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    user_label = models.CharField("Usuario (texto)", max_length=180, blank=True)
    role_label = models.CharField("Perfil", max_length=80, blank=True)
    action = models.CharField("Accion", max_length=20, choices=ACTION_CHOICES, db_index=True)
    module = models.CharField("Modulo", max_length=80, db_index=True)
    model_name = models.CharField("Entidad", max_length=120, blank=True)
    object_id = models.CharField("Identificador", max_length=64, blank=True)
    object_label = models.CharField("Registro", max_length=240, blank=True)
    description = models.CharField("Descripcion", max_length=320, blank=True)
    changes = models.JSONField("Cambios", null=True, blank=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("Navegador", max_length=320, blank=True)
    path = models.CharField("Ruta", max_length=320, blank=True)
    method = models.CharField("Metodo", max_length=10, blank=True)
    status_code = models.PositiveSmallIntegerField("Codigo HTTP", null=True, blank=True)
    duration_ms = models.PositiveIntegerField("Duracion (ms)", null=True, blank=True)

    class Meta:
        db_table = "audit_log"
        verbose_name = "Registro de auditoria"
        verbose_name_plural = "Bitacora de auditoria"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["module", "action"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.user_label} {self.action} {self.module}"
