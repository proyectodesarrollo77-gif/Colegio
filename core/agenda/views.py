"""Vistas HTML de la agenda virtual."""
from __future__ import annotations

from config.resource import ModulePageView, ResourceView, choices_to_options, column, field, remote

YEAR_OPTIONS = "/api/school-years/options/"
GROUP_OPTIONS = "/api/groups/options/"
SUBJECT_OPTIONS = "/api/subjects/options/"
PERIOD_OPTIONS = "/api/periods/options/"
ASSIGNMENT_OPTIONS = "/api/teaching-assignments/options/"

EVENT_TYPES = [
    ("ACADEMICO", "Academico"), ("INSTITUCIONAL", "Institucional"), ("CULTURAL", "Cultural"),
    ("DEPORTIVO", "Deportivo"), ("REUNION", "Reunion"), ("EVALUACION", "Evaluacion"),
    ("FESTIVO", "Festivo"), ("ENTREGA_BOLETINES", "Entrega de boletines"),
]
AUDIENCES = [
    ("TODOS", "Toda la comunidad"), ("ESTUDIANTES", "Estudiantes"), ("DOCENTES", "Docentes"),
    ("ACUDIENTES", "Acudientes"), ("DIRECTIVOS", "Directivos"), ("GRUPO", "Grupo especifico"),
]


class AgendaCalendarView(ModulePageView):
    template_name = "agenda/calendar.html"
    module_code = "agenda.calendar"
    title = "Calendario Institucional"
    subtitle = "Eventos, reuniones y fechas clave del ano escolar."
    icon = "calendar"


class AgendaEventResourceView(ResourceView):
    module_code = "agenda.calendar"
    title = "Eventos de Agenda"
    subtitle = "Administre los eventos publicados en el calendario institucional."
    icon = "calendar"
    endpoint = "/api/agenda-events/"
    columns = [
        column("title", "Evento", width=250),
        column("type_display", "Tipo", type="badge", tone="brand", width=170),
        column("start_at", "Inicio", type="datetime", width=170),
        column("place", "Lugar", width=170),
        column("audience_display", "Dirigido a", type="badge", tone="info", width=170),
        column("is_published", "Publicado", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        field("event_type", "Tipo de evento", type="select", col="half", options=choices_to_options(EVENT_TYPES)),
        field("title", "Titulo", required=True),
        field("description", "Descripcion", type="textarea"),
        field("start_at", "Inicio", type="datetime-local", required=True, col="half"),
        field("end_at", "Fin", type="datetime-local", col="half"),
        field("place", "Lugar", col="half"),
        field("audience", "Dirigido a", type="select", col="half", options=choices_to_options(AUDIENCES)),
        field("color", "Color", type="color", col="half", default="#4F46E5"),
        field("all_day", "Todo el dia", type="boolean", col="half"),
        field("is_published", "Publicado", type="boolean", col="half", default=True),
        field("send_notification", "Notificar a la comunidad", type="boolean", col="half"),
        field("attachment", "Anexo", type="file"),
    ]


class AgendaActivityView(ResourceView):
    module_code = "agenda.activities"
    title = "Actividades"
    subtitle = "Tareas, talleres y entregas asignadas a cada grupo."
    icon = "clipboard-check"
    endpoint = "/api/agenda-activities/"
    columns = [
        column("title", "Actividad", width=250),
        column("group_name", "Grupo", type="badge", tone="brand", width=130),
        column("subject_name", "Asignatura", width=180),
        column("teacher_name", "Docente", width=180),
        column("assigned_date", "Asignada", type="date", width=130),
        column("due_date", "Entrega", type="date", width=130),
        column("status", "Estado", type="badge", width=140, map={
            "PROGRAMADA": {"label": "Programada", "tone": "info"},
            "EN_CURSO": {"label": "En curso", "tone": "warning"},
            "FINALIZADA": {"label": "Finalizada", "tone": "success"},
            "CANCELADA": {"label": "Cancelada", "tone": "neutral"},
        }),
    ]
    form_fields = [
        remote("group", "Grupo", GROUP_OPTIONS, required=True, col="half"),
        remote("subject", "Asignatura", SUBJECT_OPTIONS, col="half"),
        remote("assignment", "Asignacion academica", ASSIGNMENT_OPTIONS, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, col="half"),
        field("title", "Titulo", required=True),
        field("description", "Descripcion", type="textarea"),
        field("assigned_date", "Fecha de asignacion", type="date", col="half"),
        field("due_date", "Fecha de entrega", type="date", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PROGRAMADA", "Programada"), ("EN_CURSO", "En curso"),
            ("FINALIZADA", "Finalizada"), ("CANCELADA", "Cancelada"),
        ])),
        field("notify_guardians", "Notificar acudientes", type="boolean", col="half", default=True),
        field("attachment", "Material", type="file"),
    ]
    filters = [{"name": "group", "label": "Grupo", "type": "remote", "endpoint": GROUP_OPTIONS}]


class CircularView(ResourceView):
    module_code = "agenda.mail"
    title = "Correos y Circulares"
    subtitle = "Comunicados institucionales enviados por correo y plataforma."
    icon = "mail"
    endpoint = "/api/circulars/"
    columns = [
        column("number", "Numero", type="mono", width=120),
        column("subject", "Asunto", width=280),
        column("audience_display", "Dirigido a", type="badge", tone="brand", width=170),
        column("sent_at", "Enviada", type="datetime", width=160),
        column("recipients_count", "Destinatarios", type="number", width=140, align="center"),
        column("status", "Estado", type="badge", width=140, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "PROGRAMADA": {"label": "Programada", "tone": "info"},
            "ENVIADA": {"label": "Enviada", "tone": "success"},
            "CANCELADA": {"label": "Cancelada", "tone": "danger"},
        }),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        field("number", "Numero", col="half"),
        field("subject", "Asunto", required=True),
        field("body", "Contenido", type="textarea", required=True, rows=8),
        field("audience", "Dirigido a", type="select", col="half", options=choices_to_options([
            ("TODOS", "Toda la comunidad"), ("ESTUDIANTES", "Estudiantes"), ("DOCENTES", "Docentes"),
            ("ACUDIENTES", "Acudientes"), ("GRUPO", "Grupos seleccionados"),
        ])),
        field("scheduled_at", "Programar envio", type="datetime-local", col="half"),
        field("send_email", "Enviar por correo", type="boolean", col="half", default=True),
        field("attachment", "Anexo", type="file", col="half"),
    ]
    row_actions = [{"name": "send", "label": "Enviar circular", "icon": "mail"}]
    empty_title = "Sin circulares registradas"
    empty_message = "Redacte y envie comunicados a la comunidad educativa."
