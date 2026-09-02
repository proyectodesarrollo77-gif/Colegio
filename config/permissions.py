"""
PL_SGE - Motor central de permisos por modulo y por accion.

Toda la plataforma resuelve la autorizacion a traves de este modulo:
  * Vistas HTML  -> ModulePermissionRequiredMixin
  * API REST     -> HasModulePermission / ModulePermission
  * Plantillas   -> {% if perms_map.students.create %}
"""
from __future__ import annotations

from functools import lru_cache

from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

# ---------------------------------------------------------------------------
# Acciones soportadas por el sistema de permisos
# ---------------------------------------------------------------------------
ACTION_VIEW = "view"
ACTION_CREATE = "create"
ACTION_EDIT = "edit"
ACTION_DELETE = "delete"
ACTION_EXPORT = "export"
ACTION_APPROVE = "approve"

ACTIONS = (
    ACTION_VIEW,
    ACTION_CREATE,
    ACTION_EDIT,
    ACTION_DELETE,
    ACTION_EXPORT,
    ACTION_APPROVE,
)

ACTION_LABELS = {
    ACTION_VIEW: "Consultar",
    ACTION_CREATE: "Crear",
    ACTION_EDIT: "Editar",
    ACTION_DELETE: "Eliminar",
    ACTION_EXPORT: "Exportar",
    ACTION_APPROVE: "Aprobar",
}

METHOD_ACTION_MAP = {
    "GET": ACTION_VIEW,
    "HEAD": ACTION_VIEW,
    "OPTIONS": ACTION_VIEW,
    "POST": ACTION_CREATE,
    "PUT": ACTION_EDIT,
    "PATCH": ACTION_EDIT,
    "DELETE": ACTION_DELETE,
}

CACHE_PREFIX = "plsge:perms:"
CACHE_TTL = 300

SUPER_ROLE = "SUPER_ADMIN"


# ---------------------------------------------------------------------------
# Resolucion de permisos
# ---------------------------------------------------------------------------
def _cache_key(user_id: int) -> str:
    return f"{CACHE_PREFIX}{user_id}"


def invalidate_permission_cache(user_id=None):
    """Limpia la cache de permisos de un usuario o de toda la plataforma."""
    if user_id is None:
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern(f"{CACHE_PREFIX}*")
        else:
            cache.clear()
    else:
        cache.delete(_cache_key(user_id))


def build_permission_map(user) -> dict:
    """Construye {module_code: {action: bool}} para el usuario indicado."""
    from core.users.models import Module, RolePermission, UserModulePermission

    if not user or not user.is_authenticated:
        return {}

    codes = list(Module.objects.filter(is_active=True).values_list("code", flat=True))

    if user.is_superuser or getattr(user.role, "code", None) == SUPER_ROLE:
        return {code: {action: True for action in ACTIONS} for code in codes}

    perms = {code: {action: False for action in ACTIONS} for code in codes}

    if user.role_id:
        rows = RolePermission.objects.filter(role_id=user.role_id).select_related("module")
        for row in rows:
            if row.module.code not in perms:
                continue
            perms[row.module.code] = {
                ACTION_VIEW: row.can_view,
                ACTION_CREATE: row.can_create,
                ACTION_EDIT: row.can_edit,
                ACTION_DELETE: row.can_delete,
                ACTION_EXPORT: row.can_export,
                ACTION_APPROVE: row.can_approve,
            }

    # Excepciones individuales (grant / revoke) por usuario
    overrides = UserModulePermission.objects.filter(user=user).select_related("module")
    for row in overrides:
        code = row.module.code
        if code not in perms:
            continue
        perms[code][row.action] = row.granted

    return perms


def get_permission_map(user, refresh: bool = False) -> dict:
    """Version cacheada de build_permission_map."""
    if not user or not user.is_authenticated:
        return {}
    key = _cache_key(user.pk)
    if refresh:
        cache.delete(key)
    data = cache.get(key)
    if data is None:
        data = build_permission_map(user)
        cache.set(key, data, CACHE_TTL)
    return data


def user_has_permission(user, module_code: str, action: str = ACTION_VIEW) -> bool:
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or getattr(user.role, "code", None) == SUPER_ROLE:
        return True
    perms = get_permission_map(user)
    return bool(perms.get(module_code, {}).get(action, False))


def require_permission(user, module_code: str, action: str = ACTION_VIEW):
    if not user_has_permission(user, module_code, action):
        raise PermissionDenied(
            f"No tiene permiso para {ACTION_LABELS.get(action, action)} en el modulo {module_code}."
        )


def allowed_modules(user) -> set:
    """Codigos de modulo con al menos permiso de consulta."""
    perms = get_permission_map(user)
    return {code for code, actions in perms.items() if actions.get(ACTION_VIEW)}


@lru_cache(maxsize=1)
def action_choices():
    return tuple((action, ACTION_LABELS[action]) for action in ACTIONS)


# ---------------------------------------------------------------------------
# Permisos DRF
# ---------------------------------------------------------------------------
class HasModulePermission(BasePermission):
    """
    Permiso DRF basado en `module_code` declarado en la vista.

    class StudentViewSet(BaseModelViewSet):
        module_code = "students.registry"
    """

    message = "No cuenta con permisos suficientes sobre este modulo."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or getattr(user.role, "code", None) == SUPER_ROLE:
            return True

        module_code = getattr(view, "module_code", None)
        if not module_code:
            return True

        action = getattr(view, "required_action", None)
        if action is None:
            drf_action = getattr(view, "action", None)
            action_overrides = getattr(view, "action_permissions", {}) or {}
            if drf_action and drf_action in action_overrides:
                action = action_overrides[drf_action]
            elif drf_action == "export":
                action = ACTION_EXPORT
            elif drf_action == "approve":
                action = ACTION_APPROVE
            else:
                action = METHOD_ACTION_MAP.get(request.method, ACTION_VIEW)

        return user_has_permission(user, module_code, action)


class ReadOnlyOrModulePermission(HasModulePermission):
    """Lectura para cualquier autenticado; escritura segun matriz de permisos."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return super().has_permission(request, view)


class IsSuperAdmin(BasePermission):
    message = "Accion restringida al perfil Super Administrador."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or getattr(user.role, "code", None) == SUPER_ROLE)
        )


class IsOwnerOrHasModulePermission(HasModulePermission):
    """El propietario del objeto siempre puede leer/editar su propio registro."""

    owner_field = "user"

    def has_object_permission(self, request, view, obj):
        owner_field = getattr(view, "owner_field", self.owner_field)
        owner = getattr(obj, owner_field, None)
        if owner is not None and owner == request.user:
            return True
        return self.has_permission(request, view)


# ---------------------------------------------------------------------------
# Mixins para vistas Django (HTML)
# ---------------------------------------------------------------------------
class ModulePermissionRequiredMixin:
    """
    Protege vistas HTML.

    class StudentsView(ModulePermissionRequiredMixin, TemplateView):
        module_code = "students.registry"
        required_action = "view"
    """

    module_code: str | None = None
    required_action: str = ACTION_VIEW
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        from django.contrib.auth.views import redirect_to_login

        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if self.module_code and not user_has_permission(
            request.user, self.module_code, self.required_action
        ):
            raise PermissionDenied(
                "No tiene permisos para acceder a este modulo. Contacte al administrador."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["module_code"] = self.module_code
        context["module_perms"] = get_permission_map(self.request.user).get(self.module_code, {})
        return context
