"""Vistas HTML del aula virtual."""
from __future__ import annotations

from config.resource import ResourceView, choices_to_options, column, field, remote

COURSE_OPTIONS = "/api/courses/options/"
UNIT_OPTIONS = "/api/course-units/options/"
GROUP_OPTIONS = "/api/groups/options/"
SUBJECT_OPTIONS = "/api/subjects/options/"
TEACHER_OPTIONS = "/api/teachers/options/"
YEAR_OPTIONS = "/api/school-years/options/"
PERIOD_OPTIONS = "/api/periods/options/"
ASSIGNMENT_OPTIONS = "/api/teaching-assignments/options/"


class CourseView(ResourceView):
    module_code = "classroom.courses"
    title = "Cursos"
    subtitle = "Espacios virtuales por asignatura y grupo."
    icon = "monitor-play"
    endpoint = "/api/courses/"
    template_name = "classroom/courses.html"
    columns = [
        column("title", "Curso", width=250),
        column("subject_name", "Asignatura", type="badge", tone="brand", width=180),
        column("group_name", "Grupo", width=120),
        column("teacher_name", "Docente", width=180),
        column("materials_count", "Materiales", type="number", width=120, align="center"),
        column("activities_count", "Actividades", type="number", width=130, align="center"),
        column("status", "Estado", type="badge", width=130, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "PUBLICADO": {"label": "Publicado", "tone": "success"},
            "ARCHIVADO": {"label": "Archivado", "tone": "warning"},
        }),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", YEAR_OPTIONS, required=True, col="half"),
        remote("assignment", "Asignacion academica", ASSIGNMENT_OPTIONS, col="half"),
        remote("subject", "Asignatura", SUBJECT_OPTIONS, required=True, col="half"),
        remote("group", "Grupo", GROUP_OPTIONS, required=True, col="half"),
        remote("teacher", "Docente", TEACHER_OPTIONS, col="half"),
        field("color", "Color", type="color", col="half", default="#6366F1"),
        field("title", "Titulo del curso", required=True),
        field("summary", "Descripcion", type="textarea"),
        field("cover", "Portada", type="image", col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("BORRADOR", "Borrador"), ("PUBLICADO", "Publicado"), ("ARCHIVADO", "Archivado"),
        ])),
        field("allow_submissions", "Permite entregas", type="boolean", col="half", default=True),
    ]
    row_actions = [{"name": "publish", "label": "Publicar curso", "icon": "check"}]
    empty_title = "Sin cursos creados"
    empty_message = "Cree un curso por asignatura para publicar material y actividades."


class CourseMaterialView(ResourceView):
    module_code = "classroom.materials"
    title = "Material Academico"
    subtitle = "Documentos, guias, videos y enlaces del curso."
    icon = "folder"
    endpoint = "/api/course-materials/"
    columns = [
        column("title", "Material", width=260),
        column("course_title", "Curso", type="badge", tone="brand", width=200),
        column("unit_title", "Unidad", width=170),
        column("kind_display", "Tipo", type="badge", tone="info", width=150),
        column("published_at", "Publicado", type="datetime", width=160),
        column("downloads", "Descargas", type="number", width=120, align="center"),
    ]
    form_fields = [
        remote("course", "Curso", COURSE_OPTIONS, required=True, col="half"),
        remote("unit", "Unidad", UNIT_OPTIONS, col="half"),
        field("title", "Titulo", required=True),
        field("description", "Descripcion", type="textarea"),
        field("kind", "Tipo", type="select", col="half", options=choices_to_options([
            ("DOCUMENTO", "Documento"), ("PRESENTACION", "Presentacion"), ("VIDEO", "Video"),
            ("ENLACE", "Enlace externo"), ("GUIA", "Guia de trabajo"), ("LECTURA", "Lectura"),
        ])),
        field("order", "Orden", type="number", col="half", default=0),
        field("file", "Archivo", type="file", col="half"),
        field("url", "Enlace", col="half"),
    ]
    filters = [{"name": "course", "label": "Curso", "type": "remote", "endpoint": COURSE_OPTIONS}]


class CourseActivityView(ResourceView):
    module_code = "classroom.activities"
    title = "Actividades del Aula"
    subtitle = "Tareas, talleres y quices evaluables del aula virtual."
    icon = "clipboard-check"
    endpoint = "/api/course-activities/"
    columns = [
        column("title", "Actividad", width=250),
        column("course_title", "Curso", type="badge", tone="brand", width=190),
        column("group_name", "Grupo", width=110),
        column("kind_display", "Tipo", type="badge", tone="info", width=130),
        column("due_at", "Entrega", type="datetime", width=170),
        column("submissions_count", "Entregas", type="number", width=110, align="center"),
        column("status", "Estado", type="badge", width=140, map={
            "BORRADOR": {"label": "Borrador", "tone": "neutral"},
            "PUBLICADA": {"label": "Publicada", "tone": "success"},
            "CERRADA": {"label": "Cerrada", "tone": "warning"},
            "CALIFICADA": {"label": "Calificada", "tone": "brand"},
        }),
    ]
    form_fields = [
        remote("course", "Curso", COURSE_OPTIONS, required=True, col="half"),
        remote("unit", "Unidad", UNIT_OPTIONS, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, col="half"),
        field("kind", "Tipo", type="select", col="half", options=choices_to_options([
            ("TAREA", "Tarea"), ("TALLER", "Taller"), ("QUIZ", "Quiz"),
            ("PROYECTO", "Proyecto"), ("FORO", "Foro"), ("EXPOSICION", "Exposicion"),
        ])),
        field("title", "Titulo", required=True),
        field("instructions", "Instrucciones", type="textarea", rows=5),
        field("max_score", "Nota maxima", type="number", step="0.01", col="third", default=5),
        field("weight", "Porcentaje (%)", type="number", step="0.01", col="third", default=100),
        field("status", "Estado", type="select", col="third", options=choices_to_options([
            ("BORRADOR", "Borrador"), ("PUBLICADA", "Publicada"),
            ("CERRADA", "Cerrada"), ("CALIFICADA", "Calificada"),
        ])),
        field("opens_at", "Disponible desde", type="datetime-local", col="half"),
        field("due_at", "Entrega hasta", type="datetime-local", col="half"),
        field("allow_late", "Permite entrega tardia", type="boolean", col="half"),
        field("attachment", "Material anexo", type="file", col="half"),
    ]
    row_actions = [{"name": "open-submissions", "label": "Publicar y abrir entregas", "icon": "upload"}]
    filters = [{"name": "course", "label": "Curso", "type": "remote", "endpoint": COURSE_OPTIONS}]


class CourseTrackingView(ResourceView):
    module_code = "classroom.tracking"
    title = "Seguimiento"
    subtitle = "Avance y desempeno de cada estudiante en los cursos virtuales."
    icon = "activity"
    endpoint = "/api/course-progress/"
    allow_create = False
    allow_edit = False
    allow_delete = False
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="course_title"),
        column("course_title", "Curso", type="badge", tone="brand", width=200),
        column("activities_done", "Entregadas", type="number", width=120, align="center"),
        column("activities_total", "Totales", type="number", width=110, align="center"),
        column("completion", "Avance", type="percent", width=160),
        column("average_score", "Promedio", type="grade", width=120, align="center"),
        column("last_access", "Ultimo acceso", type="datetime", width=170),
    ]
    filters = [{"name": "course", "label": "Curso", "type": "remote", "endpoint": COURSE_OPTIONS}]
    empty_title = "Sin datos de seguimiento"
    empty_message = "El avance se calcula cuando los estudiantes entregan actividades."
