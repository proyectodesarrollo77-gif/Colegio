"""Servicio central de registro de auditoria."""
from __future__ import annotations

import logging

logger = logging.getLogger("pl_sge")


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def register_audit(
    user=None,
    action="VIEW",
    module="",
    instance=None,
    request=None,
    changes=None,
    description="",
    status_code=None,
    duration_ms=None,
):
    """Crea una entrada en la bitacora. Nunca interrumpe la operacion de negocio."""
    from .models import AuditLog

    try:
        payload = {
            "user": user if getattr(user, "pk", None) else None,
            "user_label": str(user) if user else "Anonimo",
            "role_label": getattr(getattr(user, "role", None), "name", "") if user else "",
            "action": action,
            "module": module or "",
            "changes": changes,
            "description": description[:320],
            "ip_address": _client_ip(request),
            "user_agent": (request.META.get("HTTP_USER_AGENT", "")[:320] if request else ""),
            "path": (request.get_full_path()[:320] if request else ""),
            "method": (request.method if request else ""),
            "status_code": status_code,
            "duration_ms": duration_ms,
        }
        if instance is not None:
            payload["model_name"] = instance._meta.verbose_name.title()
            payload["object_id"] = str(getattr(instance, "pk", ""))[:64]
            payload["object_label"] = str(instance)[:240]
        return AuditLog.objects.create(**payload)
    except Exception as exc:  # pragma: no cover
        logger.warning("No fue posible registrar la auditoria: %s", exc)
        return None
