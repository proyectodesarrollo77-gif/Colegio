"""Vistas HTML del modulo de evaluaciones."""
from __future__ import annotations

from config.resource import ModulePageView, ResourceView, choices_to_options, column, field, remote
from core.academic.models import AcademicPeriod, SchoolYear
from core.teachers.models import TeachingAssignment

STUDENT_OPTIONS = "/api/students/options/"
PERIOD_OPTIONS = "/api/periods/options/"
SUBJECT_OPTIONS = "/api/subjects/options/"
GROUP_OPTIONS = "/api/groups/options/"
DIMENSION_OPTIONS = "/api/dimensions/options/"
PERFORMANCE_OPTIONS = "/api/grading-levels/options/"
JUDGMENT_OPTIONS = "/api/value-judgments/options/"
PURPOSE_OPTIONS = "/api/purposes/options/"


class GradeEntryView(ModulePageView):
    """Planilla de digitacion de notas por asignacion academica y periodo."""

    template_name = "evaluations/grade_entry.html"
    module_code = "evaluations.grades"
    title = "Asignacion de Notas"
    subtitle = "Digite las calificaciones de sus procesos academicos y consolide la nota del periodo."
    icon = "clipboard-check"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        year = SchoolYear.current()
        assignments = TeachingAssignment.objects.filter(
            deleted_at__isnull=True, is_active=True
        ).select_related("teacher", "subject", "group", "group__grade")
        if year:
            assignments = assignments.filter(school_year=year)

        teacher = getattr(user, "teacher_profile", None)
        if teacher and not user.is_super_admin and user.role_code in ("DOCENTE", "TUTOR"):
            assignments = assignments.filter(teacher=teacher)

        context.update(
            {
                "assignments": assignments.order_by("group__grade__order", "group__code", "subject__name"),
                "periods": AcademicPeriod.objects.filter(school_year=year).order_by("number") if year else [],
                "current_period": AcademicPeriod.objects.filter(school_year=year, is_current=True).first()
                if year
                else None,
                "school_year": year,
            }
        )
        return context


class JudgmentAssignmentView(ResourceView):
    module_code = "evaluations.judgments"
    title = "Juicios Valorativos"
    subtitle = "Asigne fortalezas, dificultades y recomendaciones a cada estudiante."
    icon = "message"
    endpoint = "/api/student-judgments/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="subject_name"),
        column("period_name", "Periodo", type="badge", tone="info", width=140),
        column("subject_name", "Asignatura", width=180),
        column("judgment_type", "Tipo", type="badge", tone="brand", width=150),
        column("text", "Juicio", type="truncate", width=340),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, required=True, col="half"),
        remote("subject", "Asignatura", SUBJECT_OPTIONS, col="half"),
        field("judgment_type", "Tipo", type="select", col="half", options=choices_to_options([
            ("DESEMPENO", "Indicador de desempeno"), ("FORTALEZA", "Fortaleza"),
            ("DEBILIDAD", "Debilidad"), ("RECOMENDACION", "Recomendacion"),
        ])),
        remote("judgment", "Juicio predefinido", JUDGMENT_OPTIONS),
        field("custom_text", "Texto personalizado", type="textarea", rows=3),
    ]
    filters = [
        {"name": "period", "label": "Periodo", "type": "remote", "endpoint": PERIOD_OPTIONS},
        {"name": "subject", "label": "Asignatura", "type": "remote", "endpoint": SUBJECT_OPTIONS},
    ]


class QualitativeView(ResourceView):
    module_code = "evaluations.qualitative"
    title = "Evaluacion Cualitativa"
    subtitle = "Valoracion descriptiva por dimension, sin nota numerica."
    icon = "book"
    endpoint = "/api/qualitative-evaluations/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="subject_name"),
        column("period_name", "Periodo", type="badge", tone="info", width=140),
        column("dimension_name", "Dimension", type="badge", tone="brand", width=170),
        column("performance_name", "Desempeno", type="badge", tone="success", width=150),
        column("description", "Valoracion", type="truncate", width=300),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, required=True, col="half"),
        remote("subject", "Asignatura", SUBJECT_OPTIONS, col="half"),
        remote("dimension", "Dimension", DIMENSION_OPTIONS, col="half"),
        remote("performance", "Desempeno", PERFORMANCE_OPTIONS, col="half"),
        field("description", "Valoracion cualitativa", type="textarea", rows=3),
        field("strengths", "Fortalezas", type="textarea", col="half", rows=3),
        field("difficulties", "Dificultades", type="textarea", col="half", rows=3),
        field("recommendations", "Recomendaciones", type="textarea", rows=3),
    ]


class PreschoolPurposeView(ResourceView):
    module_code = "evaluations.preschool"
    title = "Propositos Preescolar"
    subtitle = "Valoracion de propositos por dimension del desarrollo infantil."
    icon = "sparkles"
    endpoint = "/api/purpose-evaluations/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="dimension_name"),
        column("purpose_text", "Proposito", type="truncate", width=340),
        column("period_name", "Periodo", type="badge", tone="info", width=140),
        column("achievement", "Nivel de logro", type="badge", width=160, map={
            "SUPERADO": {"label": "Superado", "tone": "success"},
            "EN_PROCESO": {"label": "En proceso", "tone": "info"},
            "INICIADO": {"label": "Iniciado", "tone": "warning"},
            "NO_LOGRADO": {"label": "No logrado", "tone": "danger"},
        }),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, required=True, col="half"),
        remote("purpose", "Proposito", PURPOSE_OPTIONS, required=True),
        field("achievement", "Nivel de logro", type="select", col="half", options=choices_to_options([
            ("SUPERADO", "Superado"), ("EN_PROCESO", "En proceso"),
            ("INICIADO", "Iniciado"), ("NO_LOGRADO", "No logrado"),
        ])),
        field("observation", "Observacion", type="textarea"),
    ]


class BilingualView(ResourceView):
    module_code = "evaluations.bilingual"
    title = "Modulo Bilingue"
    subtitle = "Evaluacion por competencias del Marco Comun Europeo de Referencia."
    icon = "trending-up"
    endpoint = "/api/bilingual-evaluations/"
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="subject_name"),
        column("period_name", "Periodo", type="badge", tone="info", width=130),
        column("listening", "Listening", type="grade", width=100, align="center"),
        column("speaking", "Speaking", type="grade", width=100, align="center"),
        column("reading", "Reading", type="grade", width=100, align="center"),
        column("writing", "Writing", type="grade", width=100, align="center"),
        column("average", "Promedio", type="grade", width=110, align="center"),
        column("cefr_level", "MCER", type="badge", tone="brand", width=100),
    ]
    form_fields = [
        remote("student", "Estudiante", STUDENT_OPTIONS, required=True, col="half"),
        remote("period", "Periodo", PERIOD_OPTIONS, required=True, col="half"),
        remote("subject", "Asignatura bilingue", SUBJECT_OPTIONS, required=True),
        field("listening", "Listening", type="number", step="0.01", col="third"),
        field("speaking", "Speaking", type="number", step="0.01", col="third"),
        field("reading", "Reading", type="number", step="0.01", col="third"),
        field("writing", "Writing", type="number", step="0.01", col="third"),
        field("grammar", "Grammar", type="number", step="0.01", col="third"),
        field("cefr_level", "Nivel MCER", type="select", col="third", options=choices_to_options([
            ("A1", "A1 - Principiante"), ("A2", "A2 - Basico"), ("B1", "B1 - Intermedio"),
            ("B2", "B2 - Intermedio alto"), ("C1", "C1 - Avanzado"), ("C2", "C2 - Maestria"),
        ])),
        field("comments", "Comentarios", type="textarea"),
    ]
