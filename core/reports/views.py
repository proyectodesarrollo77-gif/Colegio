"""Vistas HTML del modulo de reportes."""
from __future__ import annotations

from config.resource import ModulePageView
from core.academic.models import AcademicPeriod, Group, SchoolYear

from .models import ReportDefinition


class BaseReportsView(ModulePageView):
    template_name = "reports/catalog.html"
    category = "ACADEMICO"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = SchoolYear.current()
        context.update(
            {
                "reports": ReportDefinition.objects.filter(category=self.category, is_active=True).order_by(
                    "order", "name"
                ),
                "category": self.category,
                "school_year": year,
                "periods": AcademicPeriod.objects.filter(school_year=year).order_by("number") if year else [],
                "groups": Group.objects.filter(school_year=year).select_related("grade").order_by(
                    "grade__order", "code"
                ) if year else [],
            }
        )
        return context


class AcademicReportsView(BaseReportsView):
    module_code = "reports.academic"
    category = "ACADEMICO"
    title = "Reportes Academicos"
    subtitle = "Boletines, planillas, consolidados y actas de evaluacion."
    icon = "file-text"


class StatisticalReportsView(BaseReportsView):
    module_code = "reports.statistics"
    category = "ESTADISTICO"
    title = "Reportes Estadisticos"
    subtitle = "Indicadores de desempeno, aprobacion y distribucion por area."
    icon = "bar-chart"
    template_name = "reports/statistics.html"


class AdministrativeReportsView(BaseReportsView):
    module_code = "reports.administrative"
    category = "ADMINISTRATIVO"
    title = "Reportes Administrativos"
    subtitle = "Usuarios, matriculas, planta docente y trazabilidad de accesos."
    icon = "activity"
    template_name = "reports/administrative.html"
