"""
Modelos abstractos compartidos por todos los modulos de PL_SGE.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def alive(self):
        return self.filter(deleted_at__isnull=True)


class ActiveManager(models.Manager):
    def get_queryset(self):
        return ActiveQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()


class AliveManager(models.Manager):
    """Excluye registros marcados como eliminados (borrado logico)."""

    def get_queryset(self):
        return ActiveQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Creado el", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Actualizado el", auto_now=True)

    class Meta:
        abstract = True


class AuditableModel(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Creado por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Actualizado por",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField("Eliminado el", null=True, blank=True, editable=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Eliminado por",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_deleted",
    )

    objects = models.Manager()
    alive = AliveManager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["deleted_at", "deleted_by"])

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by"])


class UUIDModel(models.Model):
    uuid = models.UUIDField("Identificador publico", default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True


class BaseModel(AuditableModel, SoftDeleteModel, UUIDModel):
    """Modelo base estandar: auditoria + borrado logico + uuid publico + estado."""

    is_active = models.BooleanField("Activo", default=True, db_index=True)

    objects = models.Manager()
    alive = AliveManager()

    class Meta:
        abstract = True


class CatalogModel(BaseModel):
    """Base para catalogos institucionales (codigo / nombre / orden)."""

    code = models.CharField("Codigo", max_length=32, db_index=True)
    name = models.CharField("Nombre", max_length=180)
    description = models.TextField("Descripcion", blank=True)
    order = models.PositiveIntegerField("Orden", default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.code} - {self.name}" if self.code else self.name


class InstitutionScopedModel(models.Model):
    """Modelos que pertenecen a una institucion concreta (multi-tenant suave)."""

    institution = models.ForeignKey(
        "institutions.Institution",
        verbose_name="Institucion",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True


class SchoolYearScopedModel(models.Model):
    school_year = models.ForeignKey(
        "academic.SchoolYear",
        verbose_name="Ano lectivo",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True
