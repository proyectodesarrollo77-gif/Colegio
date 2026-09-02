"""Vistas HTML del modulo de tutoria."""
from __future__ import annotations

from config.resource import ResourceView, choices_to_options, column, field, remote

STUDENT_OPTIONS = "/api/students/options/"
PERIOD_OPTIONS = "/api/periods/options/"
GROUP_OPTIONS = "/api/groups/options/"
TEACHER_OPTIONS = "/api/teachers/options/"
YEAR_OPTIONS = "/api/school-years/options/"
TUTOR_OPTIONS = "/api/tutors/options/"
PERFORMANCE_OPTIONS = "/api/grading-levels/options/"
COEXISTENCE_ITEM_OPTIONS = "/api/coexistence-items/options/"


class TutorView(ResourceView):
    module_code = "tutoring.tutors"
    title = "Tutores"
    subtitle = "Docentes tutores asignados al acompanamiento de cada grupo."
    icon = "heart-handshake"
    endpoint = "/api/tutors/"
    columns = [
        column("teacher_name", "Docente tutor", type="avatar", subfield="group_name"),
        column("group_name", "Grupo", type="badge", tone="brand", width=140),
        column("grade_name", "Grado", width=140),
        column("students_count", "Estudiantes", type="number", width=130, align="center"),
        column("start_date", "Desde", type="date", width=120),
        column("is_main", "Principal", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        remote("teacher", "Docente tutor", TEACHER_OPTIONS, required=True, col="half"),
        remote("group", "Grupo", GROUP_OPTIONS, required=True, col="half"),
        field("start_date", "Desde", type="date", col="half"),
        field("end_date", "Hasta", type="date", col="half"),
        field("is_main", "Tutor principal", type="boolean", col="half", default=True),
        field("notes", "Observaciones", type="textarea"),
    ]
    empty_title = "Sin tutores asignados"
    empty_message = "Asigne un docente tutor a cada grupo para habilitar el seguimiento."


class TutoringJudgmentView(ResourceView):
    module_code = "tutoring.judgments"
    title = "Juicios de Tutoria"
    subtitle = "Valoracion integral del estudiante emitida por el tutor de grupo."
    icon = "message"
    endpoint = "/api/tutoring-judgments/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("period_name", "Periodo", type="badge", tone="info", width=140),
        column("tutor_name", "Tutor", width=180),
        column("performance_name", "Desempeno global", type="badge", tone="success", width=170),
        column("recommendations", "Recomendaciones", type="truncate", width=280),
        column("published", "Publicado", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, required=True, col="half"),
        remote("tutor", "Tutor", TUTOR_OPTIONS, col="half"),
        remote("performance", "Desempeno global", PERFORMANCE_OPTIONS, col="half"),
        field("strengths", "Fortalezas", type="textarea", rows=3),
        field("difficulties", "Dificultades", type="textarea", rows=3),
        field("recommendations", "Recomendaciones", type="textarea", rows=3),
        field("commitment", "Compromisos", type="textarea", rows=3),
        field("published", "Publicar en el boletin", type="boolean", col="half"),
    ]
    filters = [{"name": "period", "label": "Periodo", "type": "remote", "endpoint": PERIOD_OPTIONS}]


class CoexistenceView(ResourceView):
    module_code = "tutoring.coexistence"
    title = "Convivencia"
    subtitle = "Valoracion de los items de convivencia por estudiante y periodo."
    icon = "heart-handshake"
    endpoint = "/api/coexistence-evaluations/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="item_name"),
        column("item_name", "Item", width=220),
        column("item_type", "Tipo", type="badge", tone="warning", width=170),
        column("period_name", "Periodo", type="badge", tone="info", width=140),
        column("score", "Valoracion", type="grade", width=120, align="center"),
        column("performance_name", "Desempeno", type="badge", tone="success", width=150),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, required=True, col="half"),
        remote("item", "Item de convivencia", COEXISTENCE_ITEM_OPTIONS, required=True, col="half"),
        remote("performance", "Desempeno", PERFORMANCE_OPTIONS, col="half"),
        field("score", "Valoracion", type="number", step="0.01", col="half"),
        field("observation", "Observacion", type="textarea"),
    ]


class TutoringReportView(ResourceView):
    module_code = "tutoring.reports"
    title = "Reportes de Tutoria"
    subtitle = "Citaciones, reuniones y acuerdos con acudientes."
    icon = "calendar"
    endpoint = "/api/tutoring-meetings/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="subject"),
        column("scheduled_at", "Fecha y hora", type="datetime", width=170),
        column("tutor_name", "Tutor", width=180),
        column("subject", "Asunto", type="truncate", width=240),
        column("status", "Estado", type="badge", width=150, map={
            "PROGRAMADA": {"label": "Programada", "tone": "info"},
            "REALIZADA": {"label": "Realizada", "tone": "success"},
            "CANCELADA": {"label": "Cancelada", "tone": "neutral"},
            "NO_ASISTIO": {"label": "No asistio", "tone": "danger"},
        }),
        column("guardian_attended", "Asistio", type="boolean", width=100, align="center"),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("tutor", "Tutor", TUTOR_OPTIONS, col="half"),
        field("scheduled_at", "Fecha y hora", type="datetime-local", required=True, col="half"),
        field("place", "Lugar", col="half"),
        field("subject", "Asunto", required=True),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PROGRAMADA", "Programada"), ("REALIZADA", "Realizada"),
            ("CANCELADA", "Cancelada"), ("NO_ASISTIO", "No asistio"),
        ])),
        field("guardian_attended", "Asistio el acudiente", type="boolean", col="half"),
        field("agreements", "Acuerdos", type="textarea", rows=4),
    ]


class ReportBlockView(ResourceView):
    module_code = "tutoring.block"
    title = "Bloqueo de Boletin"
    subtitle = "Restrinja la entrega del boletin por cartera, documentacion o disciplina."
    icon = "lock"
    endpoint = "/api/report-blocks/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="student_document"),
        column("reason_display", "Motivo", type="badge", tone="danger", width=190),
        column("detail", "Detalle", type="truncate", width=260),
        column("amount", "Valor", type="number", decimals=2, width=130, align="right"),
        column("period_name", "Periodo", width=130),
        column("blocked", "Bloqueado", type="boolean", width=120, align="center"),
        column("released_by_name", "Liberado por", width=170),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, col="half"),
        field("reason", "Motivo", type="select", col="half", options=choices_to_options([
            ("CARTERA", "Cartera pendiente"), ("DOCUMENTOS", "Documentacion incompleta"),
            ("DISCIPLINA", "Situacion disciplinaria"), ("BIBLIOTECA", "Material pendiente"),
            ("OTRO", "Otro motivo"),
        ])),
        field("amount", "Valor adeudado", type="number", step="0.01", col="half", default=0),
        field("blocked", "Boletin bloqueado", type="boolean", col="half", default=True),
        field("detail", "Detalle"),
    ]
    row_actions = [{"name": "release", "label": "Liberar bloqueo", "icon": "check"}]
    empty_title = "Sin bloqueos registrados"
    empty_message = "Los boletines se entregan sin restriccion mientras no existan bloqueos."
