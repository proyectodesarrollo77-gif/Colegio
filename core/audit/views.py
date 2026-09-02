"""Vistas HTML de auditoria y sesiones."""
from __future__ import annotations

from config.resource import ResourceView, column

ACTION_MAP = {
    "CREATE": {"label": "Creacion", "tone": "success"},
    "UPDATE": {"label": "Modificacion", "tone": "info"},
    "DELETE": {"label": "Eliminacion", "tone": "danger"},
    "VIEW": {"label": "Consulta", "tone": "neutral"},
    "EXPORT": {"label": "Exportacion", "tone": "brand"},
    "APPROVE": {"label": "Aprobacion", "tone": "success"},
    "TOGGLE": {"label": "Cambio de estado", "tone": "warning"},
    "LOGIN": {"label": "Inicio de sesion", "tone": "info"},
    "LOGOUT": {"label": "Cierre de sesion", "tone": "neutral"},
    "ERROR": {"label": "Error", "tone": "danger"},
    "PROCESS": {"label": "Proceso academico", "tone": "brand"},
}


class AuditLogView(ResourceView):
    module_code = "audit.log"
    title = "Bitacora de Acciones"
    subtitle = "Trazabilidad completa de las operaciones realizadas en la plataforma."
    icon = "shield-check"
    endpoint = "/api/audit-logs/"
    allow_create = False
    allow_edit = False
    allow_delete = False
    ordering = "-created_at"
    page_size = 50
    columns = [
        column("created_at", "Fecha y hora", type="datetime", width=170),
        column("user_label", "Usuario", type="avatar", subfield="role_label"),
        column("action", "Accion", type="badge", width=160, map=ACTION_MAP),
        column("module_name", "Modulo", width=180),
        column("object_label", "Registro", type="truncate", width=240),
        column("ip_address", "IP", type="mono", width=130),
        column("status_code", "HTTP", type="number", width=90, align="center"),
    ]
    filters = [
        {"name": "action", "label": "Todas las acciones", "type": "select",
         "options": [{"value": key, "label": value["label"]} for key, value in ACTION_MAP.items()]},
    ]
    empty_title = "Sin registros de auditoria"
    empty_message = "Las operaciones realizadas en la plataforma se registraran automaticamente."


class SessionsView(ResourceView):
    module_code = "audit.sessions"
    title = "Sesiones Activas"
    subtitle = "Sesiones abiertas por los usuarios y control de cierre remoto."
    icon = "activity"
    endpoint = "/api/user-sessions/"
    allow_create = False
    allow_edit = False
    ordering = "-last_activity"
    columns = [
        column("user_name", "Usuario", type="avatar", subfield="role_name"),
        column("ip_address", "Direccion IP", type="mono", width=140),
        column("user_agent", "Navegador", type="truncate", width=300),
        column("last_activity", "Ultima actividad", type="datetime", width=170),
        column("is_active", "Activa", type="boolean", width=100, align="center"),
    ]
    form_fields = []
    row_actions = [{"name": "close", "label": "Cerrar sesion", "icon": "log-out"}]
    empty_title = "Sin sesiones registradas"
    empty_message = "Las sesiones aparecen al iniciar sesion en la plataforma."
