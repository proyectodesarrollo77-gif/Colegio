"""Vistas HTML de enfasis y disciplinas."""
from __future__ import annotations

from config.resource import ResourceView, choices_to_options, column, field, remote

EMPHASIS_OPTIONS = "/api/emphases/options/"
EMPHASIS_GROUP_OPTIONS = "/api/emphasis-groups/options/"
YEAR_OPTIONS = "/api/school-years/options/"
TEACHER_OPTIONS = "/api/teachers/options/"
STUDENT_OPTIONS = "/api/students/options/"


class EmphasisCatalogView(ResourceView):
    module_code = "emphases.catalog"
    title = "Enfasis y Disciplinas"
    subtitle = "Catalogo de enfasis, electivas y disciplinas ofertadas."
    icon = "target"
    endpoint = "/api/emphases/"
    columns = [
        column("code", "Codigo", type="mono", width=110),
        column("name", "Enfasis", width=250),
        column("kind_display", "Tipo", type="badge", tone="brand", width=160),
        column("groups_count", "Grupos", type="number", width=100, align="center"),
        column("color", "Color", type="color", width=120),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre del enfasis", required=True),
        field("kind", "Tipo", type="select", col="half", options=choices_to_options([
            ("DEPORTIVO", "Deportivo"), ("ARTISTICO", "Artistico"), ("TECNICO", "Tecnico"),
            ("ACADEMICO", "Academico"), ("CULTURAL", "Cultural"), ("TECNOLOGICO", "Tecnologico"),
        ])),
        field("color", "Color", type="color", col="half", default="#0EA5E9"),
        field("description", "Descripcion", type="textarea"),
        field("requirements", "Requisitos", type="textarea"),
        field("image", "Imagen", type="image", col="half"),
        field("order", "Orden", type="number", col="half", default=0),
    ]


class EmphasisGroupView(ResourceView):
    module_code = "emphases.groups"
    title = "Apertura de Grupos"
    subtitle = "Grupos de enfasis, cupos, docente asignado y horario."
    icon = "users"
    endpoint = "/api/emphasis-groups/"
    columns = [
        column("name", "Grupo", width=210),
        column("emphasis_name", "Enfasis", type="badge", tone="brand", width=190),
        column("teacher_name", "Docente", width=180),
        column("grades_display", "Grados", type="truncate", width=180),
        column("enrolled_count", "Inscritos", type="number", width=110, align="center"),
        column("available_seats", "Cupos", type="number", width=100, align="center"),
        column("status", "Estado", type="badge", width=130, map={
            "PLANEADO": {"label": "Planeado", "tone": "neutral"},
            "ABIERTO": {"label": "Abierto", "tone": "success"},
            "CERRADO": {"label": "Cerrado", "tone": "warning"},
            "CANCELADO": {"label": "Cancelado", "tone": "danger"},
        }),
    ]
    form_fields = [
        remote("emphasis", "Enfasis", EMPHASIS_OPTIONS, required=True, col="half"),
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        field("code", "Codigo del grupo", required=True, col="half"),
        field("name", "Nombre del grupo", required=True, col="half"),
        remote("teacher", "Docente asignado", TEACHER_OPTIONS, col="half"),
        field("capacity", "Cupos", type="number", col="half", default=25),
        field("weekday", "Dia", type="number", col="third", default=1, min=1, max=7),
        field("start_time", "Hora de inicio", type="time", col="third"),
        field("end_time", "Hora de fin", type="time", col="third"),
        field("place", "Lugar", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PLANEADO", "Planeado"), ("ABIERTO", "Abierto"),
            ("CERRADO", "Cerrado"), ("CANCELADO", "Cancelado"),
        ])),
    ]
    row_actions = [{"name": "open", "label": "Abrir inscripciones", "icon": "check"}]


class EmphasisEnrollmentView(ResourceView):
    module_code = "emphases.enrollment"
    title = "Matriculas de Enfasis"
    subtitle = "Inscripcion de estudiantes en los grupos de enfasis."
    icon = "clipboard-check"
    endpoint = "/api/emphasis-enrollments/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("emphasis_name", "Enfasis", type="badge", tone="brand", width=190),
        column("group_name", "Grupo", width=170),
        column("enrolled_at", "Inscripcion", type="date", width=130),
        column("score", "Valoracion", type="grade", width=120, align="center"),
        column("status", "Estado", type="badge", width=150, map={
            "ACTIVA": {"label": "Activa", "tone": "success"},
            "RETIRADA": {"label": "Retirada", "tone": "danger"},
            "LISTA_ESPERA": {"label": "Lista de espera", "tone": "warning"},
            "FINALIZADA": {"label": "Finalizada", "tone": "info"},
        }),
    ]
    form_fields = [
        remote("group", "Grupo de enfasis", EMPHASIS_GROUP_OPTIONS, required=True, col="half"),
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        field("enrolled_at", "Fecha de inscripcion", type="date", col="half"),
        field("priority", "Prioridad", type="number", col="half", default=1),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("ACTIVA", "Activa"), ("RETIRADA", "Retirada"),
            ("LISTA_ESPERA", "Lista de espera"), ("FINALIZADA", "Finalizada"),
        ])),
        field("score", "Valoracion", type="number", step="0.01", col="half"),
        field("observation", "Observacion"),
    ]
    filters = [{"name": "group", "label": "Grupo", "type": "remote", "endpoint": EMPHASIS_GROUP_OPTIONS}]
