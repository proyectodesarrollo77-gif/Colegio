"""
Servicios de autenticacion: trazabilidad, 2FA, correos y recuperacion de clave.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import AccessLog, LoginAttempt, SecurityToken, TwoFactorDevice, UserSession
from .utils import browser_name, get_client_ip, get_user_agent, guess_device

logger = logging.getLogger("pl_sge")
User = get_user_model()


# ---------------------------------------------------------------------------
# Trazabilidad
# ---------------------------------------------------------------------------
def record_access(user, request=None, event="LOGIN", success=True, detail=""):
    agent = get_user_agent(request)
    log = AccessLog.objects.create(
        user=user,
        event=event,
        success=success,
        ip_address=get_client_ip(request),
        user_agent=agent,
        device=f"{guess_device(agent)} / {browser_name(agent)}",
        detail=detail[:240],
    )
    if event == "LOGIN" and success and request is not None and request.session.session_key:
        UserSession.objects.update_or_create(
            session_key=request.session.session_key,
            defaults={
                "user": user,
                "ip_address": get_client_ip(request),
                "user_agent": agent,
                "last_activity": timezone.now(),
                "is_active": True,
                "closed_at": None,
            },
        )
    if event == "LOGOUT" and request is not None and request.session.session_key:
        UserSession.objects.filter(session_key=request.session.session_key).update(
            is_active=False, closed_at=timezone.now()
        )
    return log


def record_login_attempt(identifier, request=None, success=False, reason="", user=None):
    return LoginAttempt.objects.create(
        identifier=(identifier or "")[:180],
        user=user,
        success=success,
        reason=reason[:120],
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


def record_failed_attempt(identifier, request=None, reason="Credenciales invalidas"):
    user = User.objects.filter(email__iexact=(identifier or "").strip()).first() or User.objects.filter(
        username__iexact=(identifier or "").strip()
    ).first()
    record_login_attempt(identifier, request, success=False, reason=reason, user=user)
    if user is not None:
        user.register_failed_login(
            max_attempts=settings.PLSGE["MAX_LOGIN_ATTEMPTS"],
            lock_minutes=settings.PLSGE["LOCKOUT_MINUTES"],
        )
        if user.is_locked:
            record_access(user, request, event="LOCKED", success=False, detail="Bloqueo por intentos fallidos")
    return user


def close_other_sessions(user, keep_session_key=None):
    from django.contrib.sessions.models import Session

    sessions = UserSession.objects.filter(user=user, is_active=True)
    if keep_session_key:
        sessions = sessions.exclude(session_key=keep_session_key)
    keys = list(sessions.values_list("session_key", flat=True))
    Session.objects.filter(session_key__in=keys).delete()
    sessions.update(is_active=False, closed_at=timezone.now())
    return len(keys)


# ---------------------------------------------------------------------------
# Doble factor
# ---------------------------------------------------------------------------
def get_or_create_device(user) -> TwoFactorDevice:
    device, created = TwoFactorDevice.objects.get_or_create(user=user)
    if created or not device.recovery_codes:
        device.build_recovery_codes()
    return device


def enable_two_factor(user, token: str) -> bool:
    device = get_or_create_device(user)
    if device.verify(token):
        device.confirm()
        user.two_factor_enabled = True
        user.save(update_fields=["two_factor_enabled"])
        return True
    return False


def disable_two_factor(user):
    TwoFactorDevice.objects.filter(user=user).delete()
    user.two_factor_enabled = False
    user.save(update_fields=["two_factor_enabled"])


def qr_svg(data: str, size: int = 220) -> str:
    """Genera el QR en SVG. Usa `qrcode` si esta disponible; si no, entrega el codigo manual."""
    try:
        import qrcode
        import qrcode.image.svg

        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(data, image_factory=factory, box_size=10, border=1)
        import io

        buffer = io.BytesIO()
        img.save(buffer)
        svg = buffer.getvalue().decode("utf-8")
        svg = svg.replace("<?xml version='1.0' encoding='UTF-8'?>\n", "")
        return svg.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)
    except Exception:  # pragma: no cover - dependencia opcional
        return ""


# ---------------------------------------------------------------------------
# Correos transaccionales
# ---------------------------------------------------------------------------
def _send_html_mail(subject, template, context, to):
    context.setdefault("app", settings.PLSGE)
    try:
        html = render_to_string(template, context)
    except Exception:
        html = context.get("fallback_text", subject)
    message = EmailMultiAlternatives(
        subject=f"[{settings.PLSGE['NAME']}] {subject}",
        body=context.get("fallback_text", subject),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to] if isinstance(to, str) else list(to),
    )
    message.attach_alternative(html, "text/html")
    try:
        message.send(fail_silently=True)
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("No fue posible enviar el correo a %s: %s", to, exc)
        return False


def send_password_reset(user, request=None):
    token = SecurityToken.issue(
        user,
        SecurityToken.PURPOSE_RESET,
        hours=settings.PLSGE["PASSWORD_RESET_TIMEOUT_HOURS"],
        ip=get_client_ip(request),
    )
    path = reverse("authentication:password_reset_confirm", kwargs={"token": token.token})
    url = request.build_absolute_uri(path) if request else path
    _send_html_mail(
        "Recuperacion de contrasena",
        "authentication/emails/password_reset.html",
        {
            "user": user,
            "url": url,
            "hours": settings.PLSGE["PASSWORD_RESET_TIMEOUT_HOURS"],
            "fallback_text": f"Restablezca su contrasena ingresando a: {url}",
        },
        user.email,
    )
    record_access(user, request, event="PASSWORD_RESET", detail="Solicitud de recuperacion enviada")
    return token


def send_email_verification(user, request=None):
    token = SecurityToken.issue(user, SecurityToken.PURPOSE_VERIFY, hours=48, ip=get_client_ip(request))
    path = reverse("authentication:verify_email", kwargs={"token": token.token})
    url = request.build_absolute_uri(path) if request else path
    _send_html_mail(
        "Verificacion de correo electronico",
        "authentication/emails/verify_email.html",
        {"user": user, "url": url, "fallback_text": f"Verifique su correo ingresando a: {url}"},
        user.email,
    )
    return token


def send_credentials(user, plain_password, request=None):
    _send_html_mail(
        "Credenciales de acceso a la plataforma",
        "authentication/emails/credentials.html",
        {
            "user": user,
            "password": plain_password,
            "login_url": request.build_absolute_uri(reverse("authentication:login")) if request else "/auth/login/",
            "fallback_text": f"Usuario: {user.email} / Contrasena temporal: {plain_password}",
        },
        user.email,
    )
