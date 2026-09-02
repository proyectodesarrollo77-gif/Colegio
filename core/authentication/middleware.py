"""
Middlewares de seguridad de PL_SGE.

  * TwoFactorMiddleware      -> obliga a completar el segundo factor
  * SessionActivityMiddleware -> caduca sesiones inactivas y refresca la bitacora
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

TWO_FACTOR_SESSION_KEY = "plsge_2fa_verified"
PENDING_USER_SESSION_KEY = "plsge_2fa_pending_user"

EXEMPT_PREFIXES = (
    "/auth/",
    "/static/",
    "/media/",
    "/admin/",
    "/api/auth/",
    "/api/token/",
    "/healthz",
)


def _is_exempt(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES)


class TwoFactorMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        if _is_exempt(request.path):
            return None
        if not (user.two_factor_enabled or user.two_factor_enforced):
            return None
        if request.session.get(TWO_FACTOR_SESSION_KEY):
            return None
        if not user.two_factor_enabled and user.two_factor_enforced:
            return redirect(reverse("authentication:two_factor_setup"))
        return redirect(reverse("authentication:two_factor_verify"))


class SessionActivityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        if request.path.startswith(("/static/", "/media/")):
            return None

        timeout = getattr(settings, "SESSION_IDLE_TIMEOUT", 3600)
        now = timezone.now()
        last = request.session.get("plsge_last_activity")
        if last:
            try:
                last_dt = timezone.datetime.fromisoformat(last)
                if timezone.is_naive(last_dt):
                    last_dt = timezone.make_aware(last_dt, timezone.get_current_timezone())
                if (now - last_dt).total_seconds() > timeout:
                    from .services import record_access

                    record_access(user, request, event="LOGOUT", detail="Cierre por inactividad")
                    logout(request)
                    return redirect(f"{reverse('authentication:login')}?expired=1")
            except (ValueError, TypeError):
                pass

        request.session["plsge_last_activity"] = now.isoformat()

        session_key = request.session.session_key
        if session_key:
            from .models import UserSession

            UserSession.objects.filter(session_key=session_key).update(last_activity=now)
        return None
