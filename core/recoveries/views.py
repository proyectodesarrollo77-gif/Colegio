"""Vistas HTML del modulo de recuperaciones."""
from __future__ import annotations

from config.resource import ResourceView, choices_to_options, column, field, remote

PLAN_OPTIONS = "/api/recovery-plans/options/"
SUBJECT_OPTIONS = "/api/subjects/options/"
GROUP_OPTIONS = "/api/groups/options/"
TEACHER_OPTIONS = "/api/teachers/options/"
PERIOD_OPTIONS = "/api/periods/options/"
YEAR_OPTIONS = "/api/school-years/options/"
STUDENT_OPTIONS = "/api/students/options/"

STATUS_MAP = {
    "PROGRAMADO": {"label": "Programado", "tone": "info"},
    "EN_CURSO": {"label": "En curso", "tone": "warning"},
    "EVALUADO": {"label": "Evaluado", "tone": "success"},
    "CERRADO": {"label": "Cerrado", "tone": "neutral"},
}

PLAN_FORM = [
    remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
    remote("period", "Periodo", PERIOD_OPTIONS, col="half"),
    remote("subject", "Asignatura", SUBJECT_OPTIONS, required=True, col="half"),
    remote("group", "Grupo", GROUP_OPTIONS, col="half"),
    remote("teacher", "Docente responsable", TEACHER_OPTIONS, col="half"),
    field("plan_type", "Tipo de plan", type="select", col="half", options=choices_to_options([
        ("PERIODO", "Recuperacion de periodo"), ("FINAL", "Recuperacion final"),
        ("NIVELACION", "Nivelacion"), ("HABILITACION", "Habilitacion"), ("BILINGUE", "Refuerzo bilingue"),
    ])),
    field("name", "Nombre del plan", required=True),
    field("description", "Descripcion", type="textarea"),
    field("objectives", "Objetivos", type="textarea"),
    field("start_date", "Fecha de inicio", type="date", col="third"),
    field("end_date", "Fecha de finalizacion", type="date", col="third"),
    field("evaluation_date", "Fecha de evaluacion", type="datetime-local", col="third"),
    field("maximum_score", "Nota maxima alcanzable", type="number", step="0.01", col="half", default=3.5),
    field("status", "Estado", type="select", col="half", options=choices_to_options([
        ("PROGRAMADO", "Programado"), ("EN_CURSO", "En curso"),
        ("EVALUADO", "Evaluado"), ("CERRADO", "Cerrado"),
    ])),
    field("is_bilingual", "Proceso bilingue", type="boolean", col="half"),
]


class RecoveryPlanView(ResourceView):
    module_code = "recoveries.plans"
    title = "Planes de Recuperacion"
    subtitle = "Programe procesos de nivelacion, habilitacion y recuperacion academica."
    icon = "refresh"
    endpoint = "/api/recovery-plans/"
    columns = [
        column("name", "Plan", width=240),
        column("subject_name", "Asignatura", type="badge", tone="brand", width=180),
        column("group_name", "Grupo", width=120),
        column("type_display", "Tipo", type="badge", tone="info", width=180),
        column("enrolled_count", "Inscritos", type="number", width=110, align="center"),
        column("evaluation_date", "Evaluacion", type="datetime", width=170),
        column("status", "Estado", type="badge", width=140, map=STATUS_MAP),
    ]
    form_fields = PLAN_FORM
    row_actions = [{"name": "enroll-failing", "label": "Inscribir reprobados", "icon": "users"}]
    filters = [
        {"name": "subject", "label": "Asignatura", "type": "remote", "endpoint": SUBJECT_OPTIONS},
        {"name": "status", "label": "Estado", "type": "select",
         "options": [{"value": k, "label": v["label"]} for k, v in STATUS_MAP.items()]},
    ]
    empty_title = "Sin planes de recuperacion"
    empty_message = "Programe un plan para habilitar la nivelacion de los estudiantes."


class BilingualRecoveryView(RecoveryPlanView):
    module_code = "recoveries.bilingual"
    title = "Recuperacion Bilingue"
    subtitle = "Procesos de refuerzo y recuperacion del programa bilingue."
    icon = "trending-up"
    endpoint = "/api/recovery-plans/?is_bilingual=true"


class RecoveryActivityView(ResourceView):
    module_code = "recoveries.activities"
    title = "Actividades Complementarias"
    subtitle = "Talleres y actividades que componen cada plan de recuperacion."
    icon = "clipboard-check"
    endpoint = "/api/recovery-activities/"
    columns = [
        column("name", "Actividad", width=260),
        column("plan_name", "Plan", type="badge", tone="brand", width=220),
        column("weight", "Porcentaje", type="number", decimals=2, width=120, align="right"),
        column("due_date", "Entrega", type="date", width=130),
        column("order", "Orden", type="number", width=90, align="center"),
    ]
    form_fields = [
        remote("plan", "Plan de recuperacion", PLAN_OPTIONS, required=True),
        field("name", "Nombre de la actividad", required=True, col="half"),
        field("weight", "Porcentaje (%)", type="number", step="0.01", col="half", default=100),
        field("due_date", "Fecha de entrega", type="date", col="half"),
        field("order", "Orden", type="number", col="half", default=0),
        field("description", "Descripcion", type="textarea"),
        field("resource", "Material de apoyo", type="file"),
    ]


class RecoveryResultView(ResourceView):
    module_code = "recoveries.results"
    title = "Resultados de Recuperacion"
    subtitle = "Inscritos, notas obtenidas y aplicacion al boletin."
    icon = "award"
    endpoint = "/api/recovery-enrollments/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("subject_name", "Asignatura", type="badge", tone="brand", width=180),
        column("plan_name", "Plan", type="truncate", width=200),
        column("previous_score", "Nota anterior", type="grade", width=130, align="center"),
        column("score", "Nota obtenida", type="grade", width=130, align="center"),
        column("final_score", "Definitiva", type="grade", width=120, align="center"),
        column("status", "Estado", type="badge", width=140, map={
            "INSCRITO": {"label": "Inscrito", "tone": "info"},
            "PRESENTO": {"label": "Presento", "tone": "info"},
            "NO_PRESENTO": {"label": "No presento", "tone": "danger"},
            "APROBO": {"label": "Aprobo", "tone": "success"},
            "REPROBO": {"label": "Reprobo", "tone": "danger"},
        }),
        column("applied_to_grade", "Aplicada", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        remote("plan", "Plan de recuperacion", PLAN_OPTIONS, required=True, col="half"),
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        field("previous_score", "Nota anterior", type="number", step="0.01", col="half"),
        field("score", "Nota obtenida", type="number", step="0.01", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("INSCRITO", "Inscrito"), ("PRESENTO", "Presento"), ("NO_PRESENTO", "No presento"),
            ("APROBO", "Aprobo"), ("REPROBO", "Reprobo"),
        ])),
        field("observation", "Observacion", type="textarea"),
    ]
    row_actions = [{"name": "evaluate", "label": "Registrar nota", "icon": "check"}]
    filters = [{"name": "plan", "label": "Plan", "type": "remote", "endpoint": PLAN_OPTIONS}]
