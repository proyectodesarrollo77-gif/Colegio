"""Senales del modulo PAE: trazabilidad automatica de estados."""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import PaeBeneficiary, PaeContract, PaeDocument, PaeImprovementAction


@receiver(pre_save, sender=PaeBeneficiary)
def track_beneficiary_status(sender, instance, **kwargs):
    """Guarda el estado previo para que post_save pueda registrar el historial."""
    if not instance.pk:
        instance._previous_status = None
        return
    previous = sender.objects.filter(pk=instance.pk).values("status", "group_id").first()
    instance._previous_status = previous["status"] if previous else None
    instance._previous_group_id = previous["group_id"] if previous else None


@receiver(post_save, sender=PaeBeneficiary)
def log_beneficiary_status(sender, instance, created, **kwargs):
    """Registra en el historial cualquier cambio de estado o de grupo."""
    from .models import PaeBeneficiaryHistory

    previous_status = getattr(instance, "_previous_status", None)
    previous_group_id = getattr(instance, "_previous_group_id", None)

    if created:
        PaeBeneficiaryHistory.objects.create(
            beneficiary=instance, previous_status="", new_status=instance.status,
            new_group=str(instance.group or ""), reason="Registro inicial del beneficiario",
            changed_by=instance.created_by, created_by=instance.created_by,
        )
        return

    changed_status = previous_status is not None and previous_status != instance.status
    changed_group = previous_group_id is not None and previous_group_id != instance.group_id
    if not (changed_status or changed_group):
        return

    # `services.change_beneficiary_status` deja aqui el motivo del cambio: la
    # senal es el unico punto que escribe el historial, de modo que una misma
    # transicion no queda registrada dos veces.
    reason = getattr(instance, "_history_reason", "") or "Actualizacion del beneficiario"
    instance._history_reason = ""

    PaeBeneficiaryHistory.objects.create(
        beneficiary=instance,
        previous_status=previous_status or "",
        new_status=instance.status,
        new_group=str(instance.group or ""),
        reason=reason,
        changed_by=instance.updated_by,
        created_by=instance.updated_by,
    )


@receiver(post_save, sender=PaeContract)
def close_expired_contract(sender, instance, **kwargs):
    """Marca como vencido el contrato cuya fecha final ya paso."""
    if instance.status == "VIGENTE" and instance.is_expired:
        sender.objects.filter(pk=instance.pk).update(status="VENCIDO")


@receiver(post_save, sender=PaeImprovementAction)
def mark_overdue_action(sender, instance, **kwargs):
    """Marca como vencida la accion correctiva fuera de plazo."""
    if instance.status in ("PENDIENTE", "EN_EJECUCION") and instance.is_overdue:
        sender.objects.filter(pk=instance.pk).update(status="VENCIDA")


@receiver(post_save, sender=PaeDocument)
def mark_expired_document(sender, instance, **kwargs):
    """Marca como vencido el documento cuya fecha de vigencia ya paso."""
    if instance.status == "VIGENTE" and instance.is_expired:
        sender.objects.filter(pk=instance.pk).update(status="VENCIDO")
