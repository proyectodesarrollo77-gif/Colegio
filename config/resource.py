"""
Infraestructura de paginas de recurso (CRUD) de PL_SGE.

Cada submodulo declara de forma declarativa sus columnas, filtros y campos de
formulario; la plantilla `partials/resource_page.html` y el modulo JS
`static/js/modules/crud.js` construyen la interfaz completa contra la API REST.
"""
from __future__ import annotations

from django.views.generic import TemplateView

from config.permissions import get_permission_map
from config.permissions import ModulePermissionRequiredMixin


def column(field, label, **kwargs):
    data = {"field": field, "label": label}
    data.update(kwargs)
    return data


def field(name, label, type="text", **kwargs):
    data = {"name": name, "label": label, "type": type}
    data.update(kwargs)
    return data


def remote(name, label, endpoint, **kwargs):
    return field(name, label, type="remote", endpoint=endpoint, **kwargs)


def select(name, label, options, **kwargs):
    return field(name, label, type="select", options=options, **kwargs)


def choices_to_options(choices):
    return [{"value": value, "label": label} for value, label in choices]


class ResourceView(ModulePermissionRequiredMixin, TemplateView):
    """Pagina de gestion estandar (tabla + filtros + formulario lateral)."""

    template_name = "partials/resource_page.html"

    module_code: str = ""
    title: str = ""
    subtitle: str = ""
    icon: str = "grid"
    endpoint: str = ""
    # Parametros fijos que se envian en cada consulta y exportacion del recurso
    # (por ejemplo, acotar la bitacora general a un modulo concreto).
    base_params: dict = {}
    id_field: str = "id"
    columns: list = []
    form_fields: list = []
    filters: list = []
    search_placeholder: str = "Buscar..."
    ordering: str = "-created_at"
    page_size: int = 25
    allow_create: bool = True
    allow_edit: bool = True
    allow_delete: bool = True
    allow_export: bool = True
    allow_detail: bool = False
    row_actions: list = []
    empty_title: str = "Aun no hay registros"
    empty_message: str = "Cree el primer registro para comenzar a trabajar en este modulo."
    help_text: str = ""
    stats: list = []
    breadcrumbs: list = []

    def get_columns(self):
        return self.columns

    def get_form_fields(self):
        return self.form_fields

    def get_filters(self):
        return self.filters

    def get_resource_config(self):
        perms = get_permission_map(self.request.user).get(self.module_code, {})
        if self.request.user.is_super_admin:
            perms = {action: True for action in ("view", "create", "edit", "delete", "export", "approve")}
        return {
            "module": self.module_code,
            "title": self.title,
            "endpoint": self.endpoint,
            "baseParams": self.base_params,
            "idField": self.id_field,
            "columns": self.get_columns(),
            "fields": self.get_form_fields(),
            "filters": self.get_filters(),
            "ordering": self.ordering,
            "pageSize": self.page_size,
            "searchPlaceholder": self.search_placeholder,
            "permissions": perms,
            "allow": {
                "create": self.allow_create and perms.get("create", False),
                "edit": self.allow_edit and perms.get("edit", False),
                "delete": self.allow_delete and perms.get("delete", False),
                "export": self.allow_export and perms.get("export", False),
                "detail": self.allow_detail,
            },
            "rowActions": self.row_actions,
            "empty": {"title": self.empty_title, "message": self.empty_message},
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": self.title,
                "page_subtitle": self.subtitle,
                "page_icon": self.icon,
                "help_text": self.help_text,
                "breadcrumbs": self.breadcrumbs,
                "stat_cards": self.stats,
                # Se entrega como dict: la plantilla lo serializa con |json_script
                "resource_config": self.get_resource_config(),
            }
        )
        return context


class ModulePageView(ModulePermissionRequiredMixin, TemplateView):
    """Pagina especializada (no CRUD) con encabezado estandar."""

    title = ""
    subtitle = ""
    icon = "grid"
    help_text = ""
    breadcrumbs: list = []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": self.title,
                "page_subtitle": self.subtitle,
                "page_icon": self.icon,
                "help_text": self.help_text,
                "breadcrumbs": self.breadcrumbs,
            }
        )
        return context
