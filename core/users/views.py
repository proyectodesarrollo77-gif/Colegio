"""Vistas HTML del modulo de usuarios, perfiles y Mi Perfil."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView

from config.permissions import ACTION_LABELS, ModulePermissionRequiredMixin
from config.resource import ModulePageView, ResourceView, choices_to_options, column, field, remote

from core.authentication.models import AccessLog, TwoFactorDevice, UserSession
from core.users.models import DOCUMENT_TYPES, GENDER_CHOICES, Role, User, UserCredentialCertificate

USER_FORM_FIELDS = [
    field("first_name", "Nombres", required=True, col="half"),
    field("last_name", "Apellidos", required=True, col="half"),
    field("email", "Correo electronico", type="email", required=True, col="half"),
    field("username", "Nombre de usuario", col="half", hint="Se genera automaticamente si se deja vacio."),
    field("document_type", "Tipo de documento", type="select", options=choices_to_options(DOCUMENT_TYPES), col="half"),
    field("document_number", "Numero de documento", col="half"),
    remote("role", "Perfil de acceso", "/api/roles/options/", required=True, col="half"),
    remote("institution", "Institucion", "/api/institutions/options/", col="half"),
    field("gender", "Genero", type="select", options=choices_to_options(GENDER_CHOICES), col="half"),
    field("birth_date", "Fecha de nacimiento", type="date", col="half"),
    field("phone", "Telefono", col="half"),
    field("mobile", "Celular", col="half"),
    field("address", "Direccion", col="half"),
    field("city", "Ciudad", col="half"),
    field("password", "Contrasena", type="password", col="half", hint="Vacio = se genera automaticamente."),
    field("photo", "Fotografia", type="image", col="half"),
    field("is_active", "Usuario activo", type="boolean", col="half", default=True),
    field("two_factor_enforced", "Exigir doble factor", type="boolean", col="half"),
    field("must_change_password", "Debe cambiar la contrasena", type="boolean", col="half"),
    field("notes", "Observaciones", type="textarea"),
]

USER_COLUMNS = [
    column("full_name", "Usuario", type="avatar", subfield="email"),
    column("username", "Usuario de acceso", type="mono", width=160),
    column("document_number", "Documento", width=130),
    column("role_name", "Perfil", type="badge", tone="brand", width=150),
    column("status_display", "Estado", type="badge", width=120, map={
        "ACTIVO": {"label": "Activo", "tone": "success"},
        "INACTIVO": {"label": "Inactivo", "tone": "neutral"},
        "BLOQUEADO": {"label": "Bloqueado", "tone": "danger"},
    }),
    column("two_factor_enabled", "2FA", type="boolean", width=80, align="center"),
    column("last_login", "Ultimo acceso", type="datetime", width=160),
]


class UserManagementView(ResourceView):
    module_code = "users.management"
    title = "Gestion de Usuarios"
    subtitle = "Administre las cuentas de acceso, perfiles y credenciales de la plataforma."
    icon = "users"
    endpoint = "/api/users/"
    columns = USER_COLUMNS
    form_fields = USER_FORM_FIELDS
    search_placeholder = "Buscar por nombre, correo o documento..."
    ordering = "first_name"
    empty_title = "Aun no hay usuarios registrados"
    empty_message = "Cree el primer usuario para habilitar el acceso a la plataforma."
    row_actions = [{"name": "credentials", "label": "Ver credenciales", "icon": "key"}]

    def get_filters(self):
        roles = Role.objects.filter(is_active=True).values("id", "name")
        return [
            {"name": "role", "label": "Todos los perfiles", "type": "select",
             "options": [{"value": r["id"], "label": r["name"]} for r in roles]},
            {"name": "is_active", "label": "Estado", "type": "select",
             "options": [{"value": "true", "label": "Activos"}, {"value": "false", "label": "Inactivos"}]},
            {"name": "two_factor_enabled", "label": "2FA", "type": "select",
             "options": [{"value": "true", "label": "Con 2FA"}, {"value": "false", "label": "Sin 2FA"}]},
        ]


class StudentUsersView(ResourceView):
    module_code = "users.students"
    title = "Usuarios de Estudiantes"
    subtitle = "Cuentas de acceso de los estudiantes matriculados."
    icon = "graduation-cap"
    endpoint = "/api/users/?role_code=ESTUDIANTE"
    columns = USER_COLUMNS
    form_fields = USER_FORM_FIELDS
    allow_create = False
    help_text = "Use el boton Generar usuarios para crear cuentas masivas desde el registro de estudiantes."
    empty_title = "Sin usuarios de estudiantes"
    empty_message = "Genere las cuentas desde el modulo de estudiantes o de forma masiva."
    template_name = "users/student_users.html"


class CoordinatorUsersView(ResourceView):
    module_code = "users.coordinators"
    title = "Usuarios Coordinadores"
    subtitle = "Cuentas del equipo directivo y de coordinacion academica."
    icon = "shield-check"
    endpoint = "/api/users/?role_code=COORDINADOR"
    columns = USER_COLUMNS
    form_fields = USER_FORM_FIELDS
    empty_title = "Sin coordinadores registrados"
    empty_message = "Cree la primera cuenta de coordinacion academica."


class CredentialsView(ResourceView):
    module_code = "users.credentials"
    title = "Certificados de Usuario y Contrasena"
    subtitle = "Genere e imprima las credenciales entregadas a estudiantes y acudientes."
    icon = "key"
    endpoint = "/api/credential-certificates/"
    allow_create = False
    allow_edit = False
    columns = [
        column("user_name", "Usuario", type="avatar", subfield="user_email"),
        column("username", "Usuario de acceso", type="mono", width=170),
        column("plain_password", "Contrasena", type="mono", width=140),
        column("role_name", "Perfil", type="badge", tone="brand", width=140),
        column("delivered", "Entregado", type="boolean", width=110, align="center"),
        column("created_at", "Generado", type="datetime", width=160),
    ]
    form_fields = [field("notes", "Observaciones", type="textarea")]
    row_actions = [{"name": "print", "label": "Imprimir certificado", "icon": "printer", "url": "/users/credentials/{id}/print/"}]
    empty_title = "Sin credenciales generadas"
    empty_message = "Las credenciales se generan al crear usuarios o al restablecer contrasenas."


class AccessReportView(ResourceView):
    module_code = "users.access_report"
    title = "Reporte de Accesos"
    subtitle = "Trazabilidad completa de inicios de sesion y eventos de seguridad."
    icon = "activity"
    endpoint = "/api/access-logs/"
    allow_create = False
    allow_edit = False
    allow_delete = False
    ordering = "-created_at"
    columns = [
        column("created_at", "Fecha y hora", type="datetime", width=170),
        column("user_name", "Usuario", type="avatar", subfield="user_email"),
        column("role_name", "Perfil", width=140),
        column("event_display", "Evento", type="badge", tone="info", width=160),
        column("success", "Resultado", type="boolean", width=110, align="center"),
        column("ip_address", "Direccion IP", type="mono", width=140),
        column("device", "Dispositivo", width=180),
    ]
    filters = [
        {"name": "event", "label": "Todos los eventos", "type": "select", "options": [
            {"value": "LOGIN", "label": "Inicio de sesion"},
            {"value": "LOGOUT", "label": "Cierre de sesion"},
            {"value": "2FA_OK", "label": "Verificacion 2FA"},
            {"value": "2FA_FAIL", "label": "Fallo 2FA"},
            {"value": "PASSWORD_CHANGE", "label": "Cambio de contrasena"},
            {"value": "LOCKED", "label": "Cuenta bloqueada"},
        ]},
        {"name": "success", "label": "Resultado", "type": "select", "options": [
            {"value": "true", "label": "Exitosos"}, {"value": "false", "label": "Fallidos"},
        ]},
    ]
    empty_title = "Sin registros de acceso"
    empty_message = "Los eventos de autenticacion apareceran aqui automaticamente."


class AuthenticatorView(ResourceView):
    module_code = "users.authenticator"
    title = "Google Authenticator"
    subtitle = "Administre los dispositivos de doble factor de la comunidad educativa."
    icon = "smartphone"
    endpoint = "/api/two-factor-devices/"
    allow_create = False
    allow_edit = False
    allow_delete = False
    columns = [
        column("user_name", "Usuario", type="avatar", subfield="user_email"),
        column("name", "Dispositivo", width=200),
        column("confirmed", "Confirmado", type="boolean", width=120, align="center"),
        column("confirmed_at", "Activado el", type="datetime", width=170),
        column("last_used_at", "Ultimo uso", type="datetime", width=170),
    ]
    row_actions = [{"name": "reset", "label": "Reiniciar dispositivo", "icon": "refresh"}]
    template_name = "users/authenticator.html"
    empty_title = "Sin dispositivos configurados"
    empty_message = "Los usuarios pueden activar el doble factor desde Mi Perfil > Seguridad."


# ---------------------------------------------------------------------------
# Mi perfil
# ---------------------------------------------------------------------------
class ProfileView(ModulePageView):
    template_name = "users/profile.html"
    module_code = None
    title = "Mi Perfil"
    subtitle = "Administre sus datos personales, seguridad y actividad reciente."
    icon = "user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(
            {
                "profile_user": user,
                "document_types": DOCUMENT_TYPES,
                "genders": GENDER_CHOICES,
                "device": TwoFactorDevice.objects.filter(user=user).first(),
                "sessions": UserSession.objects.filter(user=user).order_by("-last_activity")[:10],
                "recent_activity": AccessLog.objects.filter(user=user).order_by("-created_at")[:15],
                "current_session_key": self.request.session.session_key,
                "action_labels": ACTION_LABELS,
            }
        )
        return context


@login_required
def profile_update(request):
    if request.method != "POST":
        return redirect("users:profile")
    user = request.user
    for attribute in ["first_name", "last_name", "phone", "mobile", "address", "city"]:
        if attribute in request.POST:
            setattr(user, attribute, request.POST.get(attribute, "").strip())
    if request.POST.get("birth_date"):
        user.birth_date = request.POST["birth_date"]
    if request.POST.get("gender"):
        user.gender = request.POST["gender"]
    if request.POST.get("theme"):
        user.theme = request.POST["theme"]
    if request.FILES.get("photo"):
        user.photo = request.FILES["photo"]
    user.save()
    messages.success(request, "Datos personales actualizados correctamente.")
    return redirect("users:profile")


@login_required
def profile_password(request):
    if request.method != "POST":
        return redirect("users:profile")
    current = request.POST.get("current_password", "")
    new_password = request.POST.get("new_password", "")
    confirm = request.POST.get("confirm_password", "")

    if not request.user.check_password(current):
        messages.error(request, "La contrasena actual no es correcta.")
    elif new_password != confirm:
        messages.error(request, "Las contrasenas nuevas no coinciden.")
    else:
        try:
            validate_password(new_password, request.user)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            request.user.set_password(new_password)
            request.user.must_change_password = False
            request.user.save()
            update_session_auth_hash(request, request.user)
            from core.authentication.services import record_access

            record_access(request.user, request, event="PASSWORD_CHANGE")
            messages.success(request, "Contrasena actualizada correctamente.")
    return redirect("users:profile")


class ProfileSecurityView(ProfileView):
    template_name = "users/profile.html"


@login_required
def credentials_print(request, pk):
    certificate = get_object_or_404(UserCredentialCertificate, pk=pk)
    from core.institutions.models import Institution

    return render(
        request,
        "users/credentials_print.html",
        {"certificate": certificate, "institution": Institution.current()},
    )


class PermissionMatrixView(ModulePermissionRequiredMixin, TemplateView):
    """Configuracion > Acceso de Perfiles: matriz de permisos por rol."""

    template_name = "configuration/permission_matrix.html"
    module_code = "configuration.profiles"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Acceso de Perfiles",
                "page_subtitle": "Defina que puede hacer cada perfil en cada modulo de la plataforma.",
                "page_icon": "lock",
                "roles": Role.objects.filter(is_active=True).order_by("order", "name"),
                "action_labels": ACTION_LABELS,
            }
        )
        return context
