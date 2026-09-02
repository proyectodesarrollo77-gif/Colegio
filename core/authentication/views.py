"""Vistas HTML de autenticacion: login, 2FA, recuperacion y verificacion."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from core.institutions.context import SESSION_KEY as INSTITUTION_SESSION_KEY

from .middleware import TWO_FACTOR_SESSION_KEY
from .models import SecurityToken, TwoFactorDevice
from .services import (
    disable_two_factor,
    get_or_create_device,
    qr_svg,
    record_access,
    record_login_attempt,
    send_email_verification,
    send_password_reset,
)
from .utils import get_client_ip

User = get_user_model()


def _resolve_login_institution(user, institution_id, institutions):
    """
    Institucion con la que se abre la sesion.

    Reglas:
      * El Super Administrador puede entrar a cualquier institucion activa.
      * Los demas usuarios solo entran a la suya. Si eligen otra, se rechaza:
        el selector no puede convertirse en una via para ver datos ajenos.
      * Si el usuario no tiene institucion asignada, se respeta lo elegido.
    """
    from core.institutions.models import Institution

    elegida = None
    if institution_id:
        elegida = Institution.objects.filter(
            pk=institution_id, is_active=True, deleted_at__isnull=True
        ).first()
        if elegida is None:
            return None, "La institucion seleccionada no esta disponible."

    if user.is_super_admin:
        return elegida or user.institution or (institutions[0] if institutions else None), None

    if user.institution_id:
        if elegida is not None and elegida.pk != user.institution_id:
            return None, "Su usuario no pertenece a la institucion seleccionada."
        return user.institution, None

    return elegida, None


def _redirect_after_login(request, user):
    if user.must_change_password:
        return redirect("authentication:force_password_change")
    if user.two_factor_enforced and not user.two_factor_enabled:
        return redirect("authentication:two_factor_setup")
    if user.two_factor_enabled:
        return redirect("authentication:two_factor_verify")
    request.session[TWO_FACTOR_SESSION_KEY] = True
    next_url = request.POST.get("next") or request.GET.get("next")
    return redirect(next_url or settings.LOGIN_REDIRECT_URL)


@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated and request.method == "GET":
        return redirect(settings.LOGIN_REDIRECT_URL)

    from core.institutions.models import Institution

    institutions = list(
        Institution.objects.filter(is_active=True, deleted_at__isnull=True).order_by("-is_default", "name")
    )
    context = {
        "next": request.GET.get("next", ""),
        "expired": request.GET.get("expired") == "1",
        # El selector solo aparece cuando hay mas de una institucion, para no
        # estorbar en las instalaciones de una sola.
        "institutions": institutions,
        "show_institution_selector": len(institutions) > 1,
    }

    if request.method == "POST":
        identifier = (request.POST.get("identifier") or "").strip()
        password = request.POST.get("password") or ""
        remember = request.POST.get("remember_me") == "on"
        institution_id = (request.POST.get("institution") or "").strip()
        context["identifier"] = identifier
        context["selected_institution"] = institution_id

        candidate = User.objects.filter(email__iexact=identifier).first() or User.objects.filter(
            username__iexact=identifier
        ).first()

        if candidate and candidate.is_locked:
            context["error"] = (
                f"La cuenta esta bloqueada por seguridad hasta las {timezone.localtime(candidate.locked_until):%H:%M}."
            )
            record_login_attempt(identifier, request, success=False, reason="Cuenta bloqueada", user=candidate)
            return render(request, "authentication/login.html", context, status=401)

        user = authenticate(request, username=identifier, password=password)
        if user is None:
            context["error"] = "Credenciales invalidas. Verifique su correo y contrasena."
            if candidate:
                candidate.register_failed_login(
                    max_attempts=settings.PLSGE["MAX_LOGIN_ATTEMPTS"],
                    lock_minutes=settings.PLSGE["LOCKOUT_MINUTES"],
                )
                remaining = settings.PLSGE["MAX_LOGIN_ATTEMPTS"] - candidate.failed_login_attempts
                if candidate.is_locked:
                    context["error"] = "Cuenta bloqueada temporalmente por multiples intentos fallidos."
                elif remaining <= 2:
                    context["error"] += f" Le quedan {remaining} intentos."
            record_login_attempt(identifier, request, success=False, reason="Credenciales invalidas", user=candidate)
            return render(request, "authentication/login.html", context, status=401)

        if not user.is_active:
            context["error"] = "Su usuario se encuentra inactivo. Contacte al administrador."
            record_login_attempt(identifier, request, success=False, reason="Usuario inactivo", user=user)
            return render(request, "authentication/login.html", context, status=403)

        institution, error = _resolve_login_institution(user, institution_id, institutions)
        if error:
            context["error"] = error
            record_login_attempt(identifier, request, success=False, reason=error, user=user)
            return render(request, "authentication/login.html", context, status=403)

        login(request, user, backend="core.authentication.backends.EmailOrUsernameBackend")
        # El Super Administrador que no elige institucion entra a administrar la
        # plataforma, no una institucion en particular. Guardar la sesion solo
        # cuando la eligio de forma explicita es lo que distingue los dos modos.
        if institution is not None and (institution_id or not user.is_super_admin):
            request.session[INSTITUTION_SESSION_KEY] = institution.pk
        request.session[TWO_FACTOR_SESSION_KEY] = False
        request.session.set_expiry(60 * 60 * 24 * 14 if remember else settings.SESSION_COOKIE_AGE)
        user.register_successful_login(ip=get_client_ip(request))
        record_login_attempt(identifier, request, success=True, reason="OK", user=user)
        return _redirect_after_login(request, user)

    return render(request, "authentication/login.html", context)


@never_cache
def logout_view(request):
    if request.user.is_authenticated:
        record_access(request.user, request, event="LOGOUT")
    logout(request)
    messages.success(request, "Sesion finalizada correctamente.")
    return redirect("authentication:login")


# ---------------------------------------------------------------------------
# Doble factor
# ---------------------------------------------------------------------------
@login_required
@never_cache
def two_factor_setup(request):
    device = get_or_create_device(request.user)
    context = {
        "device": device,
        "secret": device.secret,
        "uri": device.provisioning_uri(),
        "qr": qr_svg(device.provisioning_uri()),
        "recovery_codes": [item["code"] for item in device.recovery_codes if not item.get("used")],
        "issuer": settings.PLSGE["OTP_ISSUER"],
    }

    if request.method == "POST":
        token = (request.POST.get("token") or "").strip()
        if device.verify(token):
            device.confirm()
            request.user.two_factor_enabled = True
            request.user.save(update_fields=["two_factor_enabled"])
            request.session[TWO_FACTOR_SESSION_KEY] = True
            record_access(request.user, request, event="2FA_OK", detail="Doble factor activado")
            messages.success(request, "Doble factor de autenticacion activado correctamente.")
            return redirect(settings.LOGIN_REDIRECT_URL)
        context["error"] = "El codigo ingresado no es valido. Verifique la hora de su dispositivo."
        record_access(request.user, request, event="2FA_FAIL", success=False)

    return render(request, "authentication/two_factor_setup.html", context)


@login_required
@never_cache
def two_factor_verify(request):
    if not request.user.two_factor_enabled:
        return redirect("authentication:two_factor_setup")
    if request.session.get(TWO_FACTOR_SESSION_KEY):
        return redirect(settings.LOGIN_REDIRECT_URL)

    context = {}
    if request.method == "POST":
        token = (request.POST.get("token") or "").strip()
        device = TwoFactorDevice.objects.filter(user=request.user).first()
        if device and device.verify(token):
            request.session[TWO_FACTOR_SESSION_KEY] = True
            record_access(request.user, request, event="2FA_OK")
            return redirect(request.POST.get("next") or settings.LOGIN_REDIRECT_URL)
        context["error"] = "Codigo incorrecto o expirado. Intente nuevamente."
        record_access(request.user, request, event="2FA_FAIL", success=False)

    return render(request, "authentication/two_factor_verify.html", context)


@login_required
def two_factor_disable(request):
    if request.method == "POST":
        disable_two_factor(request.user)
        request.session[TWO_FACTOR_SESSION_KEY] = True
        record_access(request.user, request, event="2FA_OK", detail="Doble factor desactivado")
        messages.warning(request, "El doble factor de autenticacion fue desactivado.")
    return redirect("users:profile_security")


# ---------------------------------------------------------------------------
# Recuperacion de contrasena
# ---------------------------------------------------------------------------
@never_cache
def password_reset_request(request):
    context = {}
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            send_password_reset(user, request)
        context["sent"] = True
        context["email"] = email
    return render(request, "authentication/password_reset.html", context)


@never_cache
def password_reset_confirm(request, token):
    record = SecurityToken.objects.filter(token=token, purpose=SecurityToken.PURPOSE_RESET).select_related("user").first()
    context = {"token": token, "valid": bool(record and record.is_valid)}

    if not context["valid"]:
        return render(request, "authentication/password_reset_confirm.html", context, status=400)

    if request.method == "POST":
        new_password = request.POST.get("new_password") or ""
        confirm_password = request.POST.get("confirm_password") or ""
        if new_password != confirm_password:
            context["error"] = "Las contrasenas no coinciden."
        else:
            try:
                validate_password(new_password, record.user)
            except ValidationError as exc:
                context["error"] = " ".join(exc.messages)
            else:
                user = record.user
                user.set_password(new_password)
                user.must_change_password = False
                user.failed_login_attempts = 0
                user.locked_until = None
                user.save()
                record.consume()
                record_access(user, request, event="PASSWORD_CHANGE", detail="Recuperacion de contrasena")
                messages.success(request, "Contrasena actualizada. Ya puede iniciar sesion.")
                return redirect("authentication:login")

    return render(request, "authentication/password_reset_confirm.html", context)


@login_required
@never_cache
def force_password_change(request):
    context = {}
    if request.method == "POST":
        current = request.POST.get("current_password") or ""
        new_password = request.POST.get("new_password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

        if not request.user.check_password(current):
            context["error"] = "La contrasena actual no es correcta."
        elif new_password != confirm_password:
            context["error"] = "Las contrasenas nuevas no coinciden."
        elif new_password == current:
            context["error"] = "La nueva contrasena debe ser diferente a la actual."
        else:
            try:
                validate_password(new_password, request.user)
            except ValidationError as exc:
                context["error"] = " ".join(exc.messages)
            else:
                request.user.set_password(new_password)
                request.user.must_change_password = False
                request.user.save()
                update_session_auth_hash(request, request.user)
                record_access(request.user, request, event="PASSWORD_CHANGE")
                messages.success(request, "Contrasena actualizada correctamente.")
                return _redirect_after_login(request, request.user)

    return render(request, "authentication/force_password_change.html", context)


# ---------------------------------------------------------------------------
# Verificacion de correo
# ---------------------------------------------------------------------------
def verify_email(request, token):
    record = SecurityToken.objects.filter(token=token, purpose=SecurityToken.PURPOSE_VERIFY).select_related("user").first()
    context = {"valid": bool(record and record.is_valid)}
    if context["valid"]:
        record.user.email_verified = True
        record.user.save(update_fields=["email_verified"])
        record.consume()
        context["user_email"] = record.user.email
    return render(request, "authentication/verify_email.html", context)


@login_required
def resend_verification(request):
    send_email_verification(request.user, request)
    messages.info(request, "Se envio un nuevo enlace de verificacion a su correo.")
    return redirect("users:profile")


def health(request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok", "app": settings.PLSGE["NAME"], "version": settings.PLSGE["VERSION"]})
