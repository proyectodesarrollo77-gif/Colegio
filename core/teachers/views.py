"""Vistas HTML del modulo docente."""
from __future__ import annotations

from config.resource import ModulePageView, ResourceView, choices_to_options, column, field, remote
from core.users.models import DOCUMENT_TYPES, GENDER_CHOICES

from .models import WEEKDAYS, Teacher

TEACHER_OPTIONS = "/api/teachers/options/"
ASSIGNMENT_OPTIONS = "/api/teaching-assignments/options/"
SUBJECT_OPTIONS = "/api/subjects/options/"
GROUP_OPTIONS = "/api/groups/options/"
YEAR_OPTIONS = "/api/school-years/options/"
PERIOD_OPTIONS = "/api/periods/options/"


class TeacherRegistryView(ResourceView):
    module_code = "teachers.registry"
    title = "Registro Docente"
    subtitle = "Planta docente, vinculacion, titulos y datos de contacto."
    icon = "presentation"
    endpoint = "/api/teachers/"
    columns = [
        column("full_name", "Docente", type="avatar", subfield="email"),
        column("teacher_code", "Codigo", type="mono", width=110),
        column("document_number", "Documento", width=130),
        column("profession", "Profesion", width=190),
        column("contract_display", "Vinculacion", type="badge", tone="info", width=150),
        column("load_percentage", "Carga", type="percent", width=150),
        column("status", "Estado", type="badge", width=120, map={
            "ACTIVO": {"label": "Activo", "tone": "success"},
            "LICENCIA": {"label": "En licencia", "tone": "warning"},
            "RETIRADO": {"label": "Retirado", "tone": "danger"},
            "INACTIVO": {"label": "Inactivo", "tone": "neutral"},
        }),
    ]
    form_fields = [
        field("section_basic", "Datos personales", type="section"),
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        remote("campus", "Sede", "/api/campuses/options/", col="half"),
        field("document_type", "Tipo de documento", type="select", col="half",
              options=choices_to_options(DOCUMENT_TYPES)),
        field("document_number", "Numero de documento", required=True, col="half"),
        field("first_name", "Nombres", required=True, col="half"),
        field("last_name", "Apellidos", required=True, col="half"),
        field("gender", "Genero", type="select", col="half", options=choices_to_options(GENDER_CHOICES)),
        field("birth_date", "Fecha de nacimiento", type="date", col="half"),
        field("photo", "Fotografia", type="image", col="half"),
        field("signature", "Firma digitalizada", type="image", col="half"),
        field("section_contact", "Contacto", type="section"),
        field("email", "Correo institucional", type="email", col="half"),
        field("personal_email", "Correo personal", type="email", col="half"),
        field("mobile", "Celular", col="half"),
        field("phone", "Telefono", col="half"),
        field("address", "Direccion"),
        field("section_labor", "Informacion laboral", type="section"),
        field("profession", "Profesion", col="half"),
        field("academic_title", "Titulo academico", col="half"),
        field("specialization", "Especializacion", col="half"),
        field("escalafon", "Escalafon", col="half"),
        field("contract_type", "Tipo de vinculacion", type="select", col="half",
              options=choices_to_options(Teacher.CONTRACT_CHOICES)),
        field("weekly_hours", "Horas semanales", type="number", col="half", default=22),
        field("hire_date", "Fecha de vinculacion", type="date", col="half"),
        field("end_date", "Fecha de retiro", type="date", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options(Teacher.STATUS_CHOICES)),
        field("is_tutor", "Puede ser tutor", type="boolean", col="half"),
        field("is_coordinator", "Es coordinador", type="boolean", col="half"),
        field("observations", "Observaciones", type="textarea"),
    ]
    filters = [
        {"name": "status", "label": "Estado", "type": "select",
         "options": choices_to_options(Teacher.STATUS_CHOICES)},
        {"name": "contract_type", "label": "Vinculacion", "type": "select",
         "options": choices_to_options(Teacher.CONTRACT_CHOICES)},
    ]
    row_actions = [{"name": "workload", "label": "Ver carga academica", "icon": "activity"}]
    empty_title = "Sin docentes registrados"
    empty_message = "Registre la planta docente para asignar carga academica y horarios."


class TeacherSubjectsView(ResourceView):
    module_code = "teachers.subjects"
    title = "Asignaturas por Docente"
    subtitle = "Asignacion academica de asignaturas y grupos a cada docente."
    icon = "book"
    endpoint = "/api/teaching-assignments/"
    columns = [
        column("teacher_name", "Docente", type="avatar", subfield="subject_name"),
        column("subject_name", "Asignatura", width=200),
        column("area_name", "Area", type="badge", tone="brand", width=170),
        column("group_name", "Grupo", width=120),
        column("grade_name", "Grado", width=130),
        column("weekly_hours", "IHS", type="number", width=80, align="center"),
        column("is_main", "Titular", type="boolean", width=100, align="center"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        remote("teacher", "Docente", TEACHER_OPTIONS, required=True, col="half"),
        remote("subject", "Asignatura", SUBJECT_OPTIONS, required=True, col="half"),
        remote("group", "Grupo", GROUP_OPTIONS, required=True, col="half"),
        field("weekly_hours", "Horas semanales", type="number", col="half", default=1),
        field("is_main", "Docente titular", type="boolean", col="half", default=True),
        field("notes", "Observaciones", type="textarea"),
    ]
    filters = [
        {"name": "teacher", "label": "Docente", "type": "remote", "endpoint": TEACHER_OPTIONS},
        {"name": "group", "label": "Grupo", "type": "remote", "endpoint": GROUP_OPTIONS},
    ]


class TeacherScheduleView(ResourceView):
    module_code = "teachers.schedules"
    title = "Horarios"
    subtitle = "Franjas horarias por docente, grupo y aula."
    icon = "clock"
    endpoint = "/api/schedule-slots/"
    template_name = "teachers/schedules.html"
    columns = [
        column("teacher_name", "Docente", width=200),
        column("weekday_display", "Dia", type="badge", tone="info", width=130),
        column("block", "Bloque", type="number", width=90, align="center"),
        column("start_time", "Inicio", width=100),
        column("end_time", "Fin", width=100),
        column("subject_name", "Asignatura", width=190),
        column("group_name", "Grupo", width=120),
        column("classroom", "Aula", width=100),
    ]
    form_fields = [
        remote("assignment", "Asignacion academica", ASSIGNMENT_OPTIONS, required=True),
        field("weekday", "Dia", type="select", required=True, col="half",
              options=choices_to_options([(str(v), label) for v, label in WEEKDAYS])),
        field("block", "Bloque / hora", type="number", col="half", default=1),
        field("start_time", "Hora de inicio", type="time", required=True, col="half"),
        field("end_time", "Hora de finalizacion", type="time", required=True, col="half"),
        field("classroom", "Aula", col="half"),
    ]
    filters = [{"name": "assignment__teacher", "label": "Docente", "type": "remote", "endpoint": TEACHER_OPTIONS}]


class TeacherLoadView(ModulePageView):
    template_name = "teachers/load.html"
    module_code = "teachers.load"
    title = "Carga Academica"
    subtitle = "Distribucion de horas semanales por docente y ocupacion de la planta."
    icon = "activity"


class TeacherProcessView(ResourceView):
    module_code = "teachers.processes"
    title = "Procesos Academicos del Docente"
    subtitle = "Procesos evaluables definidos por el docente para cada periodo."
    icon = "clipboard-check"
    endpoint = "/api/teacher-processes/"
    columns = [
        column("name", "Proceso", width=240),
        column("teacher_name", "Docente", width=190),
        column("subject_name", "Asignatura", width=180),
        column("group_name", "Grupo", width=110),
        column("period_name", "Periodo", type="badge", tone="info", width=140),
        column("weight", "Porcentaje", type="number", decimals=2, width=110, align="right"),
        column("due_date", "Fecha limite", type="date", width=130),
        column("is_closed", "Cerrado", type="boolean", width=100, align="center"),
    ]
    form_fields = [
        remote("assignment", "Asignacion academica", ASSIGNMENT_OPTIONS, required=True),
        remote("period", "Periodo", PERIOD_OPTIONS, required=True, col="half"),
        field("name", "Nombre del proceso", required=True, col="half"),
        field("weight", "Porcentaje (%)", type="number", step="0.01", col="half", default=100),
        field("due_date", "Fecha limite", type="date", col="half"),
        field("order", "Orden", type="number", col="half", default=0),
        field("is_closed", "Cerrado", type="boolean", col="half"),
        field("description", "Descripcion", type="textarea"),
    ]
    filters = [{"name": "period", "label": "Periodo", "type": "remote", "endpoint": PERIOD_OPTIONS}]
