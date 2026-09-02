"""Vistas HTML del modulo de asistencia."""
from __future__ import annotations

from config.resource import ModulePageView, ResourceView, column
from core.academic.models import AcademicPeriod, SchoolYear
from core.teachers.models import TeachingAssignment


class AttendanceRegisterView(ModulePageView):
    template_name = "attendance/register.html"
    module_code = "attendance.register"
    title = "Registro de Asistencia"
    subtitle = "Tome asistencia por asignatura, fecha y bloque de clase."
    icon = "calendar-check"

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
                "assignments": assignments.order_by("group__grade__order", "subject__name"),
                "periods": AcademicPeriod.objects.filter(school_year=year).order_by("number") if year else [],
                "current_period": AcademicPeriod.objects.filter(school_year=year, is_current=True).first()
                if year else None,
            }
        )
        return context


class AttendanceReportView(ResourceView):
    module_code = "attendance.report"
    title = "Reporte de Inasistencias"
    subtitle = "Consolidado de asistencia por estudiante, asignatura y periodo."
    icon = "activity"
    endpoint = "/api/attendance-summaries/"
    allow_create = False
    allow_edit = False
    allow_delete = False
    columns = [
        column("student_name", "Estudiante", type="avatar", subfield="subject_name"),
        column("period_name", "Periodo", type="badge", tone="info", width=140),
        column("subject_name", "Asignatura", width=190),
        column("total_sessions", "Sesiones", type="number", width=110, align="center"),
        column("absences", "Fallas", type="number", width=100, align="center"),
        column("justified", "Excusas", type="number", width=100, align="center"),
        column("late_arrivals", "Tardanzas", type="number", width=110, align="center"),
        column("attendance_rate", "Asistencia", type="percent", width=160),
    ]
    filters = [
        {"name": "period", "label": "Periodo", "type": "remote", "endpoint": "/api/periods/options/"},
        {"name": "subject", "label": "Asignatura", "type": "remote", "endpoint": "/api/subjects/options/"},
    ]
    empty_title = "Sin registros de asistencia"
    empty_message = "Tome asistencia desde el modulo de registro para generar el consolidado."
