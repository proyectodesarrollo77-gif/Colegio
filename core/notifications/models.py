"""Centro de notificaciones internas de la plataforma."""
from __future__ import annotations

from django.db import models
from django.utils import timezone

from config.models_base import TimeStampedModel


class Notification(TimeStampedModel):
    LEVEL_CHOICES = [
        ("info", "Informacion"),
        ("success", "Exito"),
        ("warning", "Advertencia"),
        ("danger", "Alerta"),
    ]

    recipient = models.ForeignKey(
        "users.User", verbose_name="Destinatario", on_delete=models.CASCADE, related_name="notifications"
    )
    sender = models.ForeignKey(
        "users.User", verbose_name="Remitente", null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_notifications"
    )
    title = models.CharField("Titulo", max_length=180)
    message = models.TextField("Mensaje", blank=True)
    level = models.CharField("Nivel", max_length=8, choices=LEVEL_CHOICES, default="info")
    icon = models.CharField("Icono", max_length=40, default="bell")
    module = models.CharField("Modulo", max_length=80, blank=True)
    url = models.CharField("Enlace", max_length=240, blank=True)
    read_at = models.DateTimeField("Leida el", null=True, blank=True)
    emailed = models.BooleanField("Enviada por correo", default=False)

    class Meta:
        db_table = "notification"
        verbose_name = "Notificacion"
        verbose_name_plural = "Notificaciones"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "read_at"])]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])

    @classmethod
    def push(cls, recipient, title, message="", level="info", url="", module="", icon="bell", sender=None):
        return cls.objects.create(
            recipient=recipient,
            sender=sender,
            title=title[:180],
            message=message,
            level=level,
            url=url,
            module=module,
            icon=icon,
        )

    @classmethod
    def broadcast(cls, recipients, title, message="", level="info", url="", module="", icon="bell", sender=None):
        objects = [
            cls(
                recipient=recipient,
                sender=sender,
                title=title[:180],
                message=message,
                level=level,
                url=url,
                module=module,
                icon=icon,
            )
            for recipient in recipients
        ]
        return cls.objects.bulk_create(objects)
