"""
Aislamiento de datos por institucion.

Descubre, para cada modelo, la ruta de llaves foraneas mas corta hasta
`institutions.Institution` y la usa para acotar las consultas a la institucion
activa. Asi el aislamiento se resuelve en un solo punto y no hay que tocar los
mas de cien ViewSets de la plataforma.

Ejemplos de ruta descubierta:
    student            -> institution
    academic_group     -> school_year__institution
    academic_subject   -> area__school_year__institution
    evaluation_process_grade -> assignment__group__school_year__institution
"""
from __future__ import annotations

from django.db.models import ForeignKey, OneToOneField

MAX_DEPTH = 4

# Modelos que NO se acotan: son transversales a la plataforma.
GLOBAL_MODELS = {
    "institutions.Institution",
    "users.Role",
    "users.Module",
    "users.RolePermission",
    "users.UserModulePermission",
    "audit.AuditLog",
}

# Campos de auditoria: apuntan a quien creo o modifico el registro, no a la
# institucion dueña del dato. Seguirlos daria un resultado incorrecto, por
# ejemplo acotar los estudiantes por la institucion del usuario que los cargo.
AUDIT_FIELDS = {"created_by", "updated_by", "deleted_by", "verified_by", "approved_by"}

# No se atraviesa el usuario como paso intermedio, por la misma razon: la
# institucion de un usuario no determina la del registro que toco.
OPAQUE_MODELS = {"users.User"}

_cache: dict[str, str | None] = {}


def _is_institution(model):
    return model._meta.label == "institutions.Institution"


def institution_path(model):
    """
    Ruta de consulta desde `model` hasta Institution, o None si no existe.

    El resultado se memoriza: recorrer las relaciones es costoso y la
    estructura no cambia en tiempo de ejecucion.
    """
    label = model._meta.label
    if label in _cache:
        return _cache[label]

    _cache[label] = None
    if label in GLOBAL_MODELS or _is_institution(model):
        return None

    # Busqueda en anchura: se prefiere siempre la ruta mas corta.
    frontier = [(model, "")]
    visited = {label}
    for _ in range(MAX_DEPTH):
        siguiente = []
        for current, prefix in frontier:
            for field in current._meta.get_fields():
                if not isinstance(field, (ForeignKey, OneToOneField)):
                    continue
                if not getattr(field, "concrete", False):
                    continue
                if field.name in AUDIT_FIELDS:
                    continue
                related = field.related_model
                path = f"{prefix}{field.name}"
                if _is_institution(related):
                    _cache[label] = path
                    return path
                if related._meta.label in visited or related._meta.label in OPAQUE_MODELS:
                    continue
                visited.add(related._meta.label)
                siguiente.append((related, f"{path}__"))
        if not siguiente:
            break
        frontier = siguiente
    return _cache[label]


def scope_queryset(queryset, institution, user=None):
    """
    Acota una consulta a la institucion indicada.

    Si el modelo no tiene ninguna ruta hacia Institution, se devuelve sin
    cambios: es un catalogo o una tabla transversal.

    Excepcion deliberada: el Super Administrador ve el listado completo de
    instituciones, porque es quien las administra y las crea. El resto de la
    informacion si le queda acotada a la institucion en la que trabaja, para
    que la interfaz sea coherente y no mezcle datos de varias.
    """
    if institution is None:
        return queryset

    if _is_institution(queryset.model):
        if user is not None and getattr(user, "is_super_admin", False):
            return queryset
        return queryset.filter(pk=institution.pk)

    path = institution_path(queryset.model)
    if not path:
        return queryset
    return queryset.filter(**{path: institution})


def reset_cache():
    """Limpia la memorizacion. Se usa en pruebas."""
    _cache.clear()
