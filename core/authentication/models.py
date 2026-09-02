"""
Modelos de autenticacion, doble factor y trazabilidad de accesos.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from urllib.parse import quote

from django.conf import settings
from django.db import models
from django.utils import timezone

from config.models_base import TimeStampedModel


# ---------------------------------------------------------------------------
# TOTP (Google Authenticator) - implementacion RFC 6238 sin dependencias
# ---------------------------------------------------------------------------
def generate_base32_secret(length: int = 20) -> str:
    return base64.b32encode(os.urandom(length)).decode("utf-8").replace("=", "")


def totp_token(secret: str, for_time: int | None = None, interval: int = 30, digits: int = 6) -> str:
    if for_time is None:
        for_time = int(time.time())
    counter = int(for_time // interval)
    padding = "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(secret.upper() + padding)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def verify_totp(secret: str, token: str, window: int = 1, interval: int = 30) -> bool:
    if not secret or not token:
        return False
    token = str(token).strip().replace(" ", "")
    if not token.isdigit():
        return False
    now = int(time.time())
    for drift in range(-window, window + 1):
        if hmac.compare_digest(totp_token(secret, now + drift * interval, interval), token):
            return True
    return False


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------
class TwoFactorDevice(TimeStampedModel):
    """Dispositivo TOTP asociado a un usuario (Google Authenticator / Authy)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="Usuario", on_delete=models.CASCADE, related_name="totp_device"
    )
    name = models.CharField("Nombre del dispositivo", max_length=80, default="Google Authenticator")
    secret = models.CharField("Secreto", max_length=64, default=generate_base32_secret)
    confirmed = models.BooleanField("Confirmado", default=False)
    confirmed_at = models.DateTimeField("Confirmado el", null=True, blank=True)
    last_used_at = models.DateTimeField("Ultimo uso", null=True, blank=True)
    last_counter = models.BigIntegerField("Ultimo contador", default=0)
    recovery_codes = models.JSONField("Codigos de recuperacion", default=list, blank=True)

    class Meta:
        db_table = "auth_two_factor_device"
        verbose_name = "Dispositivo 2FA"
        verbose_name_plural = "Dispositivos 2FA"

    def __str__(self):
        return f"2FA de {self.user}"

    # -- Operaciones -----------------------------------------------------
    def provisioning_uri(self):
        issuer = settings.PLSGE["OTP_ISSUER"]
        label = quote(f"{issuer}:{self.user.email}")
        return (
            f"otpauth://totp/{label}?secret={self.secret}"
            f"&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
        )

    def current_token(self):
        return totp_token(self.secret)

    def verify(self, token: str) -> bool:
        if not verify_totp(self.secret, token):
            return self.consume_recovery_code(token)
        counter = int(time.time() // 30)
        if counter <= self.last_counter:
            return False
        self.last_counter = counter
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_counter", "last_used_at"])
        return True

    def rotate_secret(self):
        self.secret = generate_base32_secret()
        self.confirmed = False
        self.confirmed_at = None
        self.recovery_codes = []
        self.save()
        return self.secret

    def build_recovery_codes(self, quantity=8):
        codes = [f"{secrets.randbelow(10**5):05d}-{secrets.randbelow(10**5):05d}" for _ in range(quantity)]
        self.recovery_codes = [{"code": code, "used": False} for code in codes]
        self.save(update_fields=["recovery_codes"])
        return codes

    def consume_recovery_code(self, code: str) -> bool:
        code = (code or "").strip()
        changed = False
        for item in self.recovery_codes:
            if item.get("code") == code and not item.get("used"):
                item["used"] = True
                changed = True
                break
        if changed:
            self.last_used_at = timezone.now()
            self.save(update_fields=["recovery_codes", "last_used_at"])
        return changed

    def confirm(self):
        self.confirmed = True
        self.confirmed_at = timezone.now()
        self.save(update_fields=["confirmed", "confirmed_at"])


class SecurityToken(TimeStampedModel):
    """Token de un solo uso para recuperacion de clave y verificacion de correo."""

    PURPOSE_RESET = "PASSWORD_RESET"
    PURPOSE_VERIFY = "EMAIL_VERIFY"
    PURPOSE_INVITE = "INVITATION"
    PURPOSE_CHOICES = [
        (PURPOSE_RESET, "Recuperacion de contrasena"),
        (PURPOSE_VERIFY, "Verificacion de correo"),
        (PURPOSE_INVITE, "Invitacion de acceso"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Usuario", on_delete=models.CASCADE, related_name="security_tokens"
    )
    token = models.CharField("Token", max_length=96, unique=True, default=secrets.token_urlsafe)
    purpose = models.CharField("Proposito", max_length=24, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField("Expira el")
    used_at = models.DateTimeField("Utilizado el", null=True, blank=True)
    ip_address = models.GenericIPAddressField("IP solicitante", null=True, blank=True)

    class Meta:
        db_table = "auth_security_token"
        verbose_name = "Token de seguridad"
        verbose_name_plural = "Tokens de seguridad"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["token", "purpose"])]

    def __str__(self):
        return f"{self.get_purpose_display()} - {self.user}"

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()

    def consume(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    @classmethod
    def issue(cls, user, purpose, hours=2, ip=None):
        cls.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=timezone.now())
        return cls.objects.create(
            user=user,
            purpose=purpose,
            token=secrets.token_urlsafe(48),
            expires_at=timezone.now() + timezone.timedelta(hours=hours),
            ip_address=ip,
        )


class LoginAttempt(TimeStampedModel):
    identifier = models.CharField("Usuario / correo", max_length=180, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="login_attempts",
    )
    success = models.BooleanField("Exitoso", default=False)
    reason = models.CharField("Motivo", max_length=120, blank=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("Navegador", max_length=320, blank=True)

    class Meta:
        db_table = "auth_login_attempt"
        verbose_name = "Intento de acceso"
        verbose_name_plural = "Intentos de acceso"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.identifier} - {'OK' if self.success else 'FALLIDO'}"


class AccessLog(TimeStampedModel):
    EVENT_CHOICES = [
        ("LOGIN", "Inicio de sesion"),
        ("LOGOUT", "Cierre de sesion"),
        ("2FA_OK", "Verificacion 2FA"),
        ("2FA_FAIL", "Fallo de verificacion 2FA"),
        ("PASSWORD_CHANGE", "Cambio de contrasena"),
        ("PASSWORD_RESET", "Recuperacion de contrasena"),
        ("LOCKED", "Cuenta bloqueada"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_logs",
    )
    event = models.CharField("Evento", max_length=24, choices=EVENT_CHOICES, db_index=True)
    success = models.BooleanField("Exitoso", default=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("Navegador", max_length=320, blank=True)
    device = models.CharField("Dispositivo", max_length=80, blank=True)
    location = models.CharField("Ubicacion", max_length=120, blank=True)
    detail = models.CharField("Detalle", max_length=240, blank=True)

    class Meta:
        db_table = "auth_access_log"
        verbose_name = "Registro de acceso"
        verbose_name_plural = "Reporte de accesos"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user} - {self.get_event_display()}"


class UserSession(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Usuario", on_delete=models.CASCADE, related_name="sessions"
    )
    session_key = models.CharField("Clave de sesion", max_length=64, unique=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    user_agent = models.CharField("Navegador", max_length=320, blank=True)
    last_activity = models.DateTimeField("Ultima actividad", default=timezone.now, db_index=True)
    is_active = models.BooleanField("Activa", default=True)
    closed_at = models.DateTimeField("Cerrada el", null=True, blank=True)

    class Meta:
        db_table = "auth_user_session"
        verbose_name = "Sesion de usuario"
        verbose_name_plural = "Sesiones de usuario"
        ordering = ["-last_activity"]

    def __str__(self):
        return f"{self.user} @ {self.ip_address}"

    def close(self):
        self.is_active = False
        self.closed_at = timezone.now()
        self.save(update_fields=["is_active", "closed_at"])
