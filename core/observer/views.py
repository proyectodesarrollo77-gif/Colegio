"""Vistas HTML del observador del estudiante."""
from __future__ import annotations

from config.resource import ModulePageView, ResourceView, choices_to_options, column, field, remote

STUDENT_OPTIONS = "/api/students/options/"
YEAR_OPTIONS = "/api/school-years/options/"
PERIOD_OPTIONS = "/api/periods/options/"
CATEGORY_OPTIONS = "/api/observation-categories/options/"

SEVERITY_MAP = {
    "TIPO_I": {"label": "Tipo I - Leve", "tone": "warning"},
    "TIPO_II": {"label": "Tipo II - Grave", "tone": "danger"},
    "TIPO_III": {"label": "Tipo III - Gravisima", "tone": "danger"},
    "POSITIVA": {"label": "Reconocimiento", "tone": "success"},
    "ACADEMICA": {"label": "Academica", "tone": "info"},
    "INFORMATIVA": {"label": "Informativa", "tone": "neutral"},
}


class ObservationCategoryView(ResourceView):
    module_code = "observer.categories"
    title = "Tipos de Observacion"
    subtitle = "Tipificacion de situaciones segun el manual de convivencia."
    icon = "list"
    endpoint = "/api/observation-categories/"
    columns = [
        column("code", "Codigo", type="mono", width=110),
        column("name", "Tipo de observacion", width=260),
        column("severity", "Tipificacion", type="badge", width=190, map=SEVERITY_MAP),
        column("manual_article", "Articulo", width=130),
        column("requires_guardian", "Cita acudiente", type="boolean", width=140, align="center"),
        column("entries_count", "Registros", type="number", width=110, align="center"),
    ]
    form_fields = [
        field("code", "Codigo", required=True, col="half"),
        field("severity", "Tipificacion", type="select", col="half", options=choices_to_options([
            ("TIPO_I", "Situacion tipo I - Leve"), ("TIPO_II", "Situacion tipo II - Grave"),
            ("TIPO_III", "Situacion tipo III - Gravisima"), ("POSITIVA", "Reconocimiento positivo"),
            ("ACADEMICA", "Seguimiento academico"), ("INFORMATIVA", "Informativa"),
        ])),
        field("name", "Nombre", required=True),
        field("description", "Descripcion", type="textarea"),
        field("manual_article", "Articulo del manual", col="half"),
        field("color", "Color", type="color", col="half", default="#F59E0B"),
        field("order", "Orden", type="number", col="half", default=0),
        field("requires_guardian", "Requiere citacion de acudiente", type="boolean", col="half"),
        field("requires_commitment", "Requiere acta de compromiso", type="boolean", col="half"),
    ]


class ObserverRecordView(ResourceView):
    module_code = "observer.records"
    title = "Registro de Observaciones"
    subtitle = "Anotaciones disciplinarias, academicas y reconocimientos del estudiante."
    icon = "eye"
    endpoint = "/api/observer-entries/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("date", "Fecha", type="date", width=120),
        column("category_name", "Tipo", width=180),
        column("severity", "Tipificacion", type="badge", width=180, map=SEVERITY_MAP),
        column("description", "Descripcion", type="truncate", width=280),
        column("guardian_notified", "Notificado", type="boolean", width=120, align="center"),
        column("status", "Estado", type="badge", width=150, map={
            "ABIERTA": {"label": "Abierta", "tone": "warning"},
            "EN_SEGUIMIENTO": {"label": "En seguimiento", "tone": "info"},
            "CERRADA": {"label": "Cerrada", "tone": "success"},
            "ANULADA": {"label": "Anulada", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        remote("category", "Tipo de observacion", CATEGORY_OPTIONS, required=True, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, col="half"),
        field("date", "Fecha del hecho", type="date", required=True, col="half"),
        field("place", "Lugar", col="half"),
        field("description", "Descripcion de la situacion", type="textarea", required=True, rows=4),
        field("student_version", "Version del estudiante", type="textarea", rows=3),
        field("actions_taken", "Acciones adoptadas", type="textarea", rows=3),
        field("commitments", "Compromisos", type="textarea", rows=3),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("ABIERTA", "Abierta"), ("EN_SEGUIMIENTO", "En seguimiento"),
            ("CERRADA", "Cerrada"), ("ANULADA", "Anulada"),
        ])),
        field("attachment", "Anexo", type="file", col="half"),
        field("student_signed", "Firmado por el estudiante", type="boolean", col="half"),
        field("guardian_signed", "Firmado por el acudiente", type="boolean", col="half"),
    ]
    filters = [
        {"name": "category", "label": "Tipo", "type": "remote", "endpoint": CATEGORY_OPTIONS},
        {"name": "status", "label": "Estado", "type": "select", "options": [
            {"value": "ABIERTA", "label": "Abiertas"},
            {"value": "EN_SEGUIMIENTO", "label": "En seguimiento"},
            {"value": "CERRADA", "label": "Cerradas"},
        ]},
    ]
    row_actions = [{"name": "notify-guardian", "label": "Notificar acudiente", "icon": "mail"}]
    empty_title = "Sin anotaciones registradas"
    empty_message = "Registre observaciones para construir el historial del estudiante."


class ObserverHistoryView(ModulePageView):
    template_name = "observer/history.html"
    module_code = "observer.history"
    title = "Historial Estudiantil"
    subtitle = "Linea de tiempo completa de anotaciones y seguimientos por estudiante."
    icon = "activity"
