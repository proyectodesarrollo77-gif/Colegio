"""Vistas HTML de la Directiva Academica."""
from __future__ import annotations

from config.resource import ResourceView, choices_to_options, column, field, remote

SCHOOL_YEAR_OPTIONS = "/api/school-years/options/"
PERIOD_OPTIONS = "/api/periods/options/"
GRADE_OPTIONS = "/api/grades/options/"
SUBJECT_OPTIONS = "/api/subjects/options/"
AREA_OPTIONS = "/api/areas/options/"
LEVEL_OPTIONS = "/api/education-levels/options/"
DIMENSION_OPTIONS = "/api/dimensions/options/"
SCALE_OPTIONS = "/api/grading-scales/options/"
PERFORMANCE_OPTIONS = "/api/grading-levels/options/"


class SchoolYearView(ResourceView):
    module_code = "academic.years"
    title = "Ano Lectivo"
    subtitle = "Configure los anos lectivos, su vigencia y estado de cierre."
    icon = "calendar"
    endpoint = "/api/school-years/"
    ordering = "-year"
    columns = [
        column("name", "Ano lectivo", width=200),
        column("year", "Ano", type="number", width=90),
        column("start_date", "Inicio", type="date", width=130),
        column("end_date", "Finalizacion", type="date", width=130),
        column("periods_count", "Periodos", type="number", width=100, align="center"),
        column("progress", "Avance", type="percent", width=150),
        column("status", "Estado", type="badge", width=130, map={
            "PLANEACION": {"label": "En planeacion", "tone": "neutral"},
            "ACTIVO": {"label": "Activo", "tone": "success"},
            "CIERRE": {"label": "En cierre", "tone": "warning"},
            "CERRADO": {"label": "Cerrado", "tone": "danger"},
        }),
        column("is_current", "En curso", type="boolean", width=100, align="center"),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        field("year", "Ano", type="number", required=True, col="half"),
        field("name", "Nombre", col="half", placeholder="Ano lectivo 2026"),
        field("weeks", "Semanas academicas", type="number", col="half", default=40),
        field("start_date", "Fecha de inicio", type="date", required=True, col="half"),
        field("end_date", "Fecha de finalizacion", type="date", required=True, col="half"),
        field("status", "Estado", type="select", col="half", options=choices_to_options([
            ("PLANEACION", "En planeacion"), ("ACTIVO", "Activo"),
            ("CIERRE", "En cierre"), ("CERRADO", "Cerrado"),
        ])),
        field("is_current", "Ano en curso", type="boolean", col="half"),
        field("enrollment_open", "Matriculas abiertas", type="boolean", col="half", default=True),
        field("grades_locked", "Bloquear digitacion de notas", type="boolean", col="half"),
    ]
    empty_title = "Sin anos lectivos"
    empty_message = "Cree el ano lectivo para habilitar periodos, grupos y matriculas."


class PeriodView(ResourceView):
    module_code = "academic.periods"
    title = "Periodo Academico"
    subtitle = "Defina los periodos, su porcentaje y las ventanas de digitacion de notas."
    icon = "calendar-check"
    endpoint = "/api/periods/"
    ordering = "number"
    columns = [
        column("name", "Periodo", width=180),
        column("school_year_name", "Ano lectivo", width=160),
        column("number", "N.", type="number", width=70, align="center"),
        column("start_date", "Inicio", type="date", width=120),
        column("end_date", "Fin", type="date", width=120),
        column("weight", "Porcentaje", type="number", decimals=2, width=110, align="right"),
        column("grades_open", "Digitacion", type="boolean", width=110, align="center"),
        column("report_published", "Boletin", type="boolean", width=100, align="center"),
        column("is_current", "Actual", type="boolean", width=90, align="center"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        field("number", "Numero de periodo", type="number", required=True, col="half"),
        field("name", "Nombre", required=True, col="half"),
        field("short_name", "Abreviatura", col="half", placeholder="P1"),
        field("start_date", "Fecha de inicio", type="date", required=True, col="half"),
        field("end_date", "Fecha de finalizacion", type="date", required=True, col="half"),
        field("weight", "Porcentaje (%)", type="number", step="0.01", col="half", default=25),
        field("is_recovery", "Periodo de recuperacion", type="boolean", col="half"),
        field("grades_open_from", "Apertura de digitacion", type="datetime-local", col="half"),
        field("grades_open_to", "Cierre de digitacion", type="datetime-local", col="half"),
        field("grades_open", "Digitacion abierta", type="boolean", col="half", default=True),
        field("is_current", "Periodo en curso", type="boolean", col="half"),
        field("report_published", "Boletin publicado", type="boolean", col="half"),
    ]
    filters = [{"name": "school_year", "label": "Ano lectivo", "type": "remote", "endpoint": SCHOOL_YEAR_OPTIONS}]


class GradingScaleView(ResourceView):
    module_code = "academic.scales"
    title = "Escala Valorativa"
    subtitle = "Escalas de calificacion y niveles de desempeno institucional."
    icon = "bar-chart"
    endpoint = "/api/grading-scales/"
    template_name = "academic/grading_scales.html"
    columns = [
        column("name", "Escala", width=220),
        column("school_year_name", "Ano lectivo", width=150),
        column("scale_type_display", "Tipo", type="badge", tone="info", width=140),
        column("minimum", "Minima", type="number", decimals=2, width=100, align="right"),
        column("passing", "Aprobatoria", type="number", decimals=2, width=120, align="right"),
        column("maximum", "Maxima", type="number", decimals=2, width=100, align="right"),
        column("is_default", "Por defecto", type="boolean", width=120, align="center"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        field("name", "Nombre de la escala", required=True, col="half"),
        field("scale_type", "Tipo", type="select", col="half", options=choices_to_options([
            ("NUMERICA", "Numerica"), ("CUALITATIVA", "Cualitativa"), ("MIXTA", "Mixta"),
        ])),
        field("decimals", "Decimales", type="number", col="half", default=1),
        field("minimum", "Valor minimo", type="number", step="0.01", col="third", default=1),
        field("passing", "Valor aprobatorio", type="number", step="0.01", col="third", default=3),
        field("maximum", "Valor maximo", type="number", step="0.01", col="third", default=5),
        field("is_default", "Escala por defecto", type="boolean", col="half"),
        field("applies_to_preschool", "Aplica a preescolar", type="boolean", col="half"),
    ]


class DimensionView(ResourceView):
    module_code = "academic.dimensions"
    title = "Dimensiones Valorativas"
    subtitle = "Dimensiones que componen la valoracion de cada asignatura."
    icon = "grid"
    endpoint = "/api/dimensions/"
    columns = [
        column("code", "Codigo", type="mono", width=110),
        column("name", "Dimension", width=240),
        column("school_year_name", "Ano lectivo", width=150),
        column("weight", "Porcentaje", type="number", decimals=2, width=120, align="right"),
        column("applies_to_all", "Todas", type="boolean", width=100, align="center"),
        column("order", "Orden", type="number", width=90, align="center"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre de la dimension", required=True),
        field("description", "Descripcion", type="textarea"),
        field("weight", "Porcentaje (%)", type="number", step="0.01", col="half", default=33.33),
        field("order", "Orden", type="number", col="half", default=0),
        field("applies_to_all", "Aplica a todas las asignaturas", type="boolean", col="half", default=True),
    ]


class AreaView(ResourceView):
    module_code = "academic.areas"
    title = "Areas"
    subtitle = "Areas obligatorias y fundamentales del plan de estudios."
    icon = "folder"
    endpoint = "/api/areas/"
    columns = [
        column("code", "Codigo", type="mono", width=110),
        column("name", "Area", width=280),
        column("school_year_name", "Ano lectivo", width=150),
        column("subjects_count", "Asignaturas", type="number", width=120, align="center"),
        column("weight", "Peso", type="number", decimals=2, width=100, align="right"),
        column("is_mandatory", "Obligatoria", type="boolean", width=120, align="center"),
        column("color", "Color", type="color", width=120),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre del area", required=True),
        field("description", "Descripcion", type="textarea"),
        field("weight", "Porcentaje del area (%)", type="number", step="0.01", col="half", default=100),
        field("order", "Orden", type="number", col="half", default=0),
        field("color", "Color", type="color", col="half", default="#6366F1"),
        field("is_mandatory", "Area obligatoria", type="boolean", col="half", default=True),
        field("average_by_intensity", "Promediar por intensidad horaria", type="boolean", col="half", default=True),
    ]


class SubjectView(ResourceView):
    module_code = "academic.subjects"
    title = "Asignaturas"
    subtitle = "Asignaturas por area, intensidad horaria y reglas de evaluacion."
    icon = "book"
    endpoint = "/api/subjects/"
    columns = [
        column("code", "Codigo", type="mono", width=110),
        column("name", "Asignatura", width=250),
        column("area_name", "Area", type="badge", tone="brand", width=180),
        column("weekly_hours", "IHS", type="number", width=80, align="center"),
        column("weight", "Peso", type="number", decimals=2, width=90, align="right"),
        column("is_bilingual", "Bilingue", type="boolean", width=100, align="center"),
        column("affects_promotion", "Promocion", type="boolean", width=110, align="center"),
    ]
    form_fields = [
        remote("area", "Area", AREA_OPTIONS, required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre de la asignatura", required=True),
        field("description", "Descripcion", type="textarea"),
        field("weekly_hours", "Intensidad horaria semanal", type="number", col="third", default=1),
        field("weight", "Peso dentro del area (%)", type="number", step="0.01", col="third", default=100),
        field("order", "Orden", type="number", col="third", default=0),
        field("evaluation_type", "Tipo de evaluacion", type="select", col="half", options=choices_to_options([
            ("CUANTITATIVA", "Cuantitativa"), ("CUALITATIVA", "Cualitativa"),
        ])),
        field("is_bilingual", "Asignatura bilingue", type="boolean", col="half"),
        field("affects_promotion", "Afecta la promocion", type="boolean", col="half", default=True),
        field("allows_recovery", "Permite recuperacion", type="boolean", col="half", default=True),
    ]
    filters = [{"name": "area", "label": "Area", "type": "remote", "endpoint": AREA_OPTIONS}]


class EducationLevelView(ResourceView):
    module_code = "academic.levels"
    title = "Niveles Educativos"
    subtitle = "Preescolar, basica primaria, basica secundaria y media."
    icon = "layers"
    endpoint = "/api/education-levels/"
    columns = [
        column("code", "Codigo", type="mono", width=110),
        column("name", "Nivel educativo", width=280),
        column("grades_count", "Grados", type="number", width=100, align="center"),
        column("is_preschool", "Preescolar", type="boolean", width=120, align="center"),
        column("evaluation_type", "Evaluacion", type="badge", tone="info", width=150),
        column("order", "Orden", type="number", width=90, align="center"),
    ]
    form_fields = [
        remote("institution", "Institucion", "/api/institutions/options/", required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre del nivel", required=True),
        field("description", "Descripcion", type="textarea"),
        field("evaluation_type", "Tipo de evaluacion", type="select", col="half", options=choices_to_options([
            ("CUANTITATIVA", "Cuantitativa"), ("CUALITATIVA", "Cualitativa"), ("MIXTA", "Mixta"),
        ])),
        field("order", "Orden", type="number", col="half", default=0),
        field("is_preschool", "Es preescolar", type="boolean", col="half"),
    ]


class GradeView(ResourceView):
    module_code = "academic.grades"
    title = "Grados"
    subtitle = "Grados escolares, edades sugeridas y ruta de promocion."
    icon = "list"
    endpoint = "/api/grades/"
    columns = [
        column("code", "Codigo", type="mono", width=100),
        column("name", "Grado", width=200),
        column("level_name", "Nivel", type="badge", tone="brand", width=200),
        column("numeric_value", "Valor", type="number", width=90, align="center"),
        column("groups_count", "Grupos", type="number", width=100, align="center"),
        column("is_graduation", "Graduacion", type="boolean", width=120, align="center"),
    ]
    form_fields = [
        remote("level", "Nivel educativo", LEVEL_OPTIONS, required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre del grado", required=True, col="half"),
        field("numeric_value", "Valor numerico", type="number", col="half", default=0),
        remote("next_grade", "Grado siguiente", GRADE_OPTIONS, col="half"),
        field("order", "Orden", type="number", col="half", default=0),
        field("minimum_age", "Edad minima", type="number", col="half", default=0),
        field("maximum_age", "Edad maxima", type="number", col="half", default=0),
        field("is_graduation", "Grado de graduacion", type="boolean", col="half"),
    ]
    filters = [{"name": "level", "label": "Nivel educativo", "type": "remote", "endpoint": LEVEL_OPTIONS}]


class GroupView(ResourceView):
    module_code = "academic.groups"
    title = "Grupos"
    subtitle = "Grupos por grado, sede y jornada con su director de grupo."
    icon = "users"
    endpoint = "/api/groups/"
    columns = [
        column("name", "Grupo", width=170),
        column("grade_name", "Grado", type="badge", tone="brand", width=150),
        column("level_name", "Nivel", width=170),
        column("director_name", "Director de grupo", width=200),
        column("enrolled_count", "Matriculados", type="number", width=130, align="center"),
        column("occupancy", "Ocupacion", type="percent", width=150),
        column("classroom", "Aula", width=100),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        remote("grade", "Grado", GRADE_OPTIONS, required=True, col="half"),
        field("code", "Codigo del grupo", required=True, col="half", placeholder="601"),
        field("name", "Nombre del grupo", required=True, col="half", placeholder="Sexto 01"),
        remote("campus", "Sede", "/api/campuses/options/", col="half"),
        remote("shift", "Jornada", "/api/shifts/options/", col="half"),
        remote("director", "Director de grupo", "/api/teachers/options/", col="half"),
        field("capacity", "Cupo maximo", type="number", col="half", default=35),
        field("classroom", "Aula", col="half"),
        field("order", "Orden", type="number", col="half", default=0),
    ]
    filters = [
        {"name": "school_year", "label": "Ano lectivo", "type": "remote", "endpoint": SCHOOL_YEAR_OPTIONS},
        {"name": "grade", "label": "Grado", "type": "remote", "endpoint": GRADE_OPTIONS},
    ]
    row_actions = [{"name": "students", "label": "Ver estudiantes", "icon": "users"}]


class AcademicProcessView(ResourceView):
    module_code = "academic.processes"
    title = "Procesos Academicos"
    subtitle = "Procesos evaluables predefinidos por asignatura y periodo."
    icon = "clipboard-check"
    endpoint = "/api/academic-processes/"
    columns = [
        column("code", "Codigo", type="mono", width=110),
        column("name", "Proceso", width=250),
        column("subject_name", "Asignatura", width=180),
        column("period_name", "Periodo", type="badge", tone="info", width=150),
        column("dimension_name", "Dimension", width=170),
        column("weight", "Porcentaje", type="number", decimals=2, width=120, align="right"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, col="half"),
        remote("subject", "Asignatura", SUBJECT_OPTIONS, col="half"),
        remote("dimension", "Dimension", DIMENSION_OPTIONS, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre del proceso", required=True, col="half"),
        field("description", "Descripcion", type="textarea"),
        field("weight", "Porcentaje (%)", type="number", step="0.01", col="half", default=100),
        field("order", "Orden", type="number", col="half", default=0),
        field("applies_to_all_subjects", "Aplica a todas las asignaturas", type="boolean", col="half"),
    ]


class ValueJudgmentView(ResourceView):
    module_code = "academic.judgments"
    title = "Juicios Valorativos"
    subtitle = "Banco de indicadores de desempeno, fortalezas y recomendaciones."
    icon = "message"
    endpoint = "/api/value-judgments/"
    columns = [
        column("text", "Juicio valorativo", type="truncate", width=420),
        column("type_display", "Tipo", type="badge", tone="info", width=160),
        column("subject_name", "Asignatura", width=170),
        column("grade_name", "Grado", width=130),
        column("performance_name", "Desempeno", type="badge", tone="success", width=140),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        field("judgment_type", "Tipo de juicio", type="select", col="half", options=choices_to_options([
            ("DESEMPENO", "Indicador de desempeno"), ("FORTALEZA", "Fortaleza"),
            ("DEBILIDAD", "Debilidad"), ("RECOMENDACION", "Recomendacion"),
        ])),
        remote("subject", "Asignatura", SUBJECT_OPTIONS, col="half"),
        remote("grade", "Grado", GRADE_OPTIONS, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, col="half"),
        remote("performance_level", "Desempeno asociado", PERFORMANCE_OPTIONS, col="half"),
        field("code", "Codigo", col="half"),
        field("order", "Orden", type="number", col="half", default=0),
        field("text", "Texto del juicio", type="textarea", required=True, rows=4),
    ]
    filters = [
        {"name": "judgment_type", "label": "Tipo", "type": "select", "options": [
            {"value": "DESEMPENO", "label": "Indicador de desempeno"},
            {"value": "FORTALEZA", "label": "Fortaleza"},
            {"value": "DEBILIDAD", "label": "Debilidad"},
            {"value": "RECOMENDACION", "label": "Recomendacion"},
        ]},
        {"name": "subject", "label": "Asignatura", "type": "remote", "endpoint": SUBJECT_OPTIONS},
    ]


class CoexistenceView(ResourceView):
    module_code = "academic.coexistence"
    title = "Convivencia"
    subtitle = "Items de convivencia valorados por el tutor o director de grupo."
    icon = "heart-handshake"
    endpoint = "/api/coexistence-items/"
    columns = [
        column("code", "Codigo", type="mono", width=110),
        column("name", "Item de convivencia", width=300),
        column("type_display", "Tipo", type="badge", tone="warning", width=180),
        column("weight", "Porcentaje", type="number", decimals=2, width=120, align="right"),
        column("affects_report", "En boletin", type="boolean", width=120, align="center"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        field("code", "Codigo", required=True, col="half"),
        field("name", "Nombre del item", required=True),
        field("item_type", "Tipo", type="select", col="half", options=choices_to_options([
            ("COMPORTAMIENTO", "Comportamiento"), ("PUNTUALIDAD", "Puntualidad"),
            ("PRESENTACION", "Presentacion personal"), ("RESPONSABILIDAD", "Responsabilidad"),
            ("CONVIVENCIA", "Convivencia"),
        ])),
        field("weight", "Porcentaje (%)", type="number", step="0.01", col="half", default=100),
        field("description", "Descripcion", type="textarea"),
        field("order", "Orden", type="number", col="half", default=0),
        field("affects_report", "Aparece en el boletin", type="boolean", col="half", default=True),
    ]


class PurposeView(ResourceView):
    module_code = "academic.purposes"
    title = "Propositos"
    subtitle = "Propositos de preescolar por dimension del desarrollo."
    icon = "sparkles"
    endpoint = "/api/purposes/"
    columns = [
        column("text", "Proposito", type="truncate", width=440),
        column("dimension_name", "Dimension", type="badge", tone="brand", width=190),
        column("grade_name", "Grado", width=140),
        column("period_name", "Periodo", width=140),
        column("order", "Orden", type="number", width=90, align="center"),
    ]
    form_fields = [
        remote("school_year", "Ano lectivo", SCHOOL_YEAR_OPTIONS, required=True, col="half"),
        remote("grade", "Grado", GRADE_OPTIONS, col="half"),
        remote("dimension", "Dimension del desarrollo", DIMENSION_OPTIONS, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, col="half"),
        field("code", "Codigo", col="half"),
        field("order", "Orden", type="number", col="half", default=0),
        field("text", "Proposito", type="textarea", required=True, rows=4),
    ]
