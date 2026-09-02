"""Middleware de auditoria: registra operaciones de escritura en la plataforma."""
from __future__ import annotations

import time

from django.utils.deprecation import MiddlewareMixin

TRACKED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
IGNORED_PREFIXES = ("/static/", "/media/", "/admin/jsi18n/", "/healthz")
ACTION_BY_METHOD = {"POST": "CREATE", "PUT": "UPDATE", "PATCH": "UPDATE", "DELETE": "DELETE"}


class AuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._audit_started = time.monotonic()
        return None

    def process_response(self, request, response):
        try:
            if request.method not in TRACKED_METHODS:
                return response
            path = request.path
            if any(path.startswith(prefix) for prefix in IGNORED_PREFIXES):
                return response
            user = getattr(request, "user", None)
            if user is None or not user.is_authenticated:
                return response
            if getattr(request, "_audit_registered", False):
                return response
            if response.status_code >= 400:
                action = "ERROR"
            else:
                action = ACTION_BY_METHOD.get(request.method, "UPDATE")

            from .services import register_audit

            duration = None
            if hasattr(request, "_audit_started"):
                duration = int((time.monotonic() - request._audit_started) * 1000)

            module = path.strip("/").split("/")
            module_code = module[1] if len(module) > 1 and module[0] == "api" else (module[0] if module else "")

            register_audit(
                user=user,
                action=action,
                module=module_code,
                request=request,
                status_code=response.status_code,
                duration_ms=duration,
                description=f"{request.method} {path}",
            )
        except Exception:  # pragma: no cover
            pass
        return response
