"""Construye la navegacion lateral segun los permisos del usuario."""
from __future__ import annotations

from django.urls import NoReverseMatch, reverse

from config.permissions import get_permission_map
from core.configuration.modules import GROUP_ORDER, MODULE_REGISTRY
from core.institutions.context import in_institution_mode


def _safe_reverse(url_name):
    if not url_name:
        return None
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return None


def navigation(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"nav_groups": [], "perms_map": {}, "solo_plataforma": False}

    perms = get_permission_map(user)
    current_path = request.path
    # El Super Administrador tiene todos los permisos en true, asi que las
    # pantallas que no le corresponden no se pueden ocultar por permisos: se
    # marcan en el registro de modulos.
    es_super_admin = user.is_super_admin
    # Mientras no haya entrado a una institucion, solo administra la
    # plataforma: la operacion academica pertenece a una institucion concreta
    # y sin elegirla no significa nada.
    solo_plataforma = es_super_admin and not in_institution_mode(request)

    def oculto(entry):
        if not es_super_admin:
            return False
        if entry.get("hide_for_super_admin", False):
            return True
        return solo_plataforma and not entry.get("platform", False)

    groups: dict[str, list] = {}
    for module in MODULE_REGISTRY:
        if oculto(module):
            continue
        children = []
        for child in module.get("children", []):
            if oculto(child):
                continue
            if not perms.get(child["code"], {}).get("view"):
                continue
            url = _safe_reverse(child.get("url"))
            children.append(
                {
                    "code": child["code"],
                    "name": child["name"],
                    "url": url,
                    "is_active": bool(url) and current_path == url,
                }
            )

        parent_visible = perms.get(module["code"], {}).get("view", False)
        if not children and not parent_visible:
            continue
        if module.get("children") and not children:
            continue

        url = _safe_reverse(module.get("url"))
        item = {
            "code": module["code"],
            "name": module["name"],
            "icon": module.get("icon", "circle"),
            "url": url,
            "children": children,
            "is_active": (bool(url) and current_path == url) or any(c["is_active"] for c in children),
            "is_open": any(c["is_active"] for c in children),
        }
        groups.setdefault(module.get("group", "Principal"), []).append(item)

    nav_groups = [
        {"name": name, "items": groups[name]}
        for name in GROUP_ORDER
        if groups.get(name)
    ]
    for name, items in groups.items():
        if name not in GROUP_ORDER:
            nav_groups.append({"name": name, "items": items})

    return {
        "nav_groups": nav_groups,
        "perms_map": perms,
        "solo_plataforma": solo_plataforma,
    }
