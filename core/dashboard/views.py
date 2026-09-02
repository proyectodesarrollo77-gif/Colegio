"""Vista principal del dashboard."""
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.academic.models import AcademicPeriod, SchoolYear
from core.agenda.models import AgendaEvent
from core.institutions.context import in_institution_mode

from .services import platform_dashboard


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard de la institucion, o panorama de la plataforma.

    El Super Administrador que aun no ha entrado a ninguna institucion no tiene
    de que ver matricula ni promedios: lo suyo es como esta funcionando cada
    institucion. Al entrar a una con `Ingresar`, ve el dashboard normal de esa
    institucion, igual que cualquier otro perfil.
    """

    def get_template_names(self):
        if self._solo_plataforma:
            return ["dashboard/platform.html"]
        return ["dashboard/index.html"]

    @property
    def _solo_plataforma(self):
        return self.request.user.is_super_admin and not in_institution_mode(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["module_code"] = "dashboard"

        if self._solo_plataforma:
            context.update(platform_dashboard())
            context.update({
                "page_title": "Panorama de la plataforma",
                "page_subtitle": "Instituciones registradas y como esta funcionando cada una.",
                "page_icon": "grid",
            })
            return context

        year = SchoolYear.current()
        context.update(
            {
                "page_title": "Dashboard",
                "page_subtitle": "Panorama general de la institucion en tiempo real.",
                "page_icon": "layout-dashboard",
                "school_year": year,
                "current_period": AcademicPeriod.objects.filter(school_year=year, is_current=True).first()
                if year
                else None,
                "upcoming_events": AgendaEvent.objects.filter(
                    is_published=True, deleted_at__isnull=True
                ).order_by("start_at")[:6],
            }
        )
        return context
